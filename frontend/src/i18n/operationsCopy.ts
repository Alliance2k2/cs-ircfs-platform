import { useI18n } from "./index";
import { operations } from "./en.operations";
export function useOperationsCopy() {
  const { t }=useI18n();
  return (english:string,values?:Record<string,string|number>)=> {
    const key=`operations.${english}` as keyof typeof operations;
    return Object.prototype.hasOwnProperty.call(operations,key) ? t(key,values) : english;
  };
}
