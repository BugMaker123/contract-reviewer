"""Central SQL visibility boundary, including legacy modules with direct SQL."""
import re
from .security import actor, PUBLIC_KINDS


class ScopedConnection:
    def __init__(self, connection):
        self.connection=connection

    def __getattr__(self,name):
        return getattr(self.connection,name)

    def execute(self,sql,params=()):
        current=actor.get()
        if not current:
            return self.connection.execute(sql,params)
        params=list(params)
        if sql.lstrip().upper().startswith('SELECT') and 'records.all' not in current['permissions']:
            # IDs are generated hex strings, but bind this predicate by literal
            # escaping as it appears before the legacy positional parameters.
            user_id=current['id'].replace("'","''")
            public=["kind IN ('category','template_group')"]
            for kind,permission,condition in [
                ('checklist','checklists.maintain',"json_extract(data,'$.published')=1"),
                ('contract_template','templates.maintain',"json_extract(data,'$.review_status')='published'"),
                ('checklist_version','checklists.maintain','0=1'),
                ('template_release','templates.maintain',"EXISTS (SELECT 1 FROM objects template_parent WHERE template_parent.id=visible.parent AND json_extract(template_parent.data,'$.review_status')='published')")]:
                public.append("(kind='"+kind+"'"+('' if permission in current['permissions'] or permission.replace('.maintain','.publish') in current['permissions'] else ' AND '+condition)+')')
            shared_source="(kind='source' AND EXISTS (SELECT 1 FROM objects source_template WHERE source_template.kind='contract_template' AND json_extract(source_template.data,'$.source_id')=visible.id AND "
            shared_source += ('1=1' if set(current['permissions']) & {'templates.maintain','templates.publish'} else "json_extract(source_template.data,'$.review_status')='published'") + '))'
            condition="owner_user_id='"+user_id+"' OR "+' OR '.join(public)+ ' OR '+shared_source
            scoped='(SELECT * FROM objects visible WHERE '+condition+')'
            def scope_table(match):
                following=re.match(r'\s+(\w+)',sql[match.end():])
                reserved={'where','order','group','limit','offset','left','right','inner','join','on','union','having'}
                alias='' if following and following[1].lower() not in reserved else ' AS objects'
                return match[1]+' '+scoped+alias
            sql=re.sub(r'\b(FROM|JOIN) objects\b',scope_table,sql,flags=re.I)
        # Stamp every insert, including immutable run/release/history records
        # inserted by legacy transactional methods.
        match=re.match(r'INSERT INTO objects\(([^)]+)\) VALUES\(([^)]+)\)',sql,re.I)
        if match and 'owner_user_id' not in match[1]:
            columns=[c.strip() for c in match[1].split(',')]
            values=dict(zip(columns,params))
            owner=None if values.get('kind') in PUBLIC_KINDS else current['id']
            if values.get('parent') and owner:
                row=self.connection.execute('SELECT owner_user_id FROM objects WHERE id=?',(values['parent'],)).fetchone()
                if row:
                    owner=row['owner_user_id']
            sql=sql[:match.start()]+ 'INSERT INTO objects('+match[1]+',owner_user_id,created_by,updated_by) VALUES('+match[2]+',?,?,?)'+sql[match.end():]
            params.extend([owner,current['id'],current['id']])
        if sql.upper().startswith('UPDATE OBJECTS SET '):
            sql=sql.replace(' SET ',' SET updated_by=?,',1)
            params.insert(0,current['id'])
        return self.connection.execute(sql,params)
