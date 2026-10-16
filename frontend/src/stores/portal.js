import { createContext } from "../portal/core/context.js";
import { setup as setupModel } from "../portal/features/model.js";

let shell;
export function usePortalShell() {
  if (!shell) {
    shell = createContext("shell", ["tasks"]);
    Object.assign(shell, setupModel(shell));
  }
  return shell;
}
