export function setup(context) {
  const { busy, showModel, modelTest, model, api, notify } = context;
  const saveModel = () => {
    if(context.auth.web) { location.assign('/admin/model'); return; }
    try {
      localStorage.setItem("LEXIS_API_KEY", model.api_key);
      localStorage.setItem("LEXIS_BASE_URL", model.base_url);
      localStorage.setItem("LEXIS_MODEL_NAME", model.model_name);
      showModel.value = false;
      notify("模型配置已保存");
    } catch {
      modelTest.value = { success: false, message: "当前浏览器无法保存配置" };
    }
  };
  const testModel = async () => {
    busy.value = true;
    try {
      modelTest.value = await api("/api/model/check", "POST", model);
    } catch (err) {
      modelTest.value = { success: false, message: err.message };
    } finally {
      busy.value = false;
    }
  };

  return { saveModel, testModel };
}
