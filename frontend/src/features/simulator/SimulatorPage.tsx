import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Phone, PhoneOff, Send } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { z } from "zod";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { apiSend } from "@/services/api/client";

const ussdSchema = z.object({ response: z.string(), english: z.string().nullable().optional(), record_type: z.string().nullable().optional(), record_id: z.number().nullable().optional() });
const smsSchema = z.object({ reply: z.string(), reply_status: z.string().optional(), record_type: z.string().nullable().optional(), record_id: z.number().nullable().optional() });

interface Trace {
  id: number;
  channel: "USSD" | "SMS";
  sent: string;
  reply: string;
  english?: string | null;
  record?: string | null;
}

const screenText = (response: string) => response.replace(/^(CON|END) /, "");

/** The on-screen phone: the real *801# menu and SMS keywords, recorded as simulator data and never sent. */
export function SimulatorPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const [phone, setPhone] = useState("+250788000001");
  const [english, setEnglish] = useState(true);
  const [session, setSession] = useState<{ id: string; steps: string[]; screen: string; english: string | null; ended: boolean } | null>(null);
  const [answer, setAnswer] = useState("");
  const [sms, setSms] = useState("");
  const [thread, setThread] = useState<{ side: "out" | "in" | "error"; text: string }[]>([]);
  const [trace, setTrace] = useState<Trace[]>([]);
  const counter = useRef(0);
  const log = (item: Omit<Trace, "id">) => setTrace((items) => [{ ...item, id: ++counter.current }, ...items].slice(0, 30));
  const refresh = () => void client.invalidateQueries({ queryKey: ["api"] });

  const ussd = useMutation({
    mutationFn: ({ id, steps }: { id: string; steps: string[] }) =>
      apiSend("POST", "simulator/ussd", { sessionId: id, serviceCode: "*801#", phoneNumber: phone, text: steps.join("*") }, ussdSchema),
    onSuccess: (data, { id, steps }) => {
      setSession({ id, steps, screen: screenText(data.response), english: data.english ? screenText(data.english) : null, ended: data.response.startsWith("END ") });
      log({ channel: "USSD", sent: steps.length ? steps.join("*") : "*801#", reply: data.response, english: data.english, record: data.record_type });
      setAnswer("");
      if (data.record_type) refresh();
    },
    onError: (error: Error, { id, steps }) => setSession({ id, steps, screen: `${t("sim.problem")}\n${error.message}`, english: null, ended: true }),
  });

  const sendSms = useMutation({
    mutationFn: (text: string) => apiSend("POST", "simulator/sms", { from: phone, to: "8448", text }, smsSchema),
    onSuccess: (data, text) => {
      setThread((items) => [...items, { side: "in", text: data.reply }]);
      log({ channel: "SMS", sent: text, reply: data.reply, record: data.record_type });
      if (data.record_type) refresh();
    },
    onError: (error: Error) => setThread((items) => [...items, { side: "error", text: `${t("sim.notDelivered")}: ${error.message}` }]),
  });

  const dial = () => ussd.mutate({ id: `sim-${Date.now().toString(36)}`, steps: [] });
  const reply = (event: FormEvent) => {
    event.preventDefault();
    if (!session || !answer.trim()) return;
    ussd.mutate({ id: session.id, steps: [...session.steps, answer.trim()] });
  };
  const submitSms = (event: FormEvent) => {
    event.preventDefault();
    const text = sms.trim();
    if (!text) return;
    setThread((items) => [...items, { side: "out", text }]);
    setSms("");
    sendSms.mutate(text);
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow={t("sim.eyebrow")} title={t("sim.title")} description={t("sim.description")} />
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-64"><TextField label={t("sim.phone")} value={phone} onChange={(event) => setPhone(event.target.value)} inputMode="tel" /></div>
        <label className="flex h-10 items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={english} onChange={(event) => setEnglish(event.target.checked)} className="h-4 w-4" />
          {t("sim.english")}
        </label>
        <Badge tone="warning">{t("sim.badge")}</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title={`USSD ${t("sim.code")}`} />
          <div className="p-5">
            <div className="mx-auto max-w-sm rounded-[2rem] border-4 border-forest bg-forest-deep p-4 shadow-raised">
              <div aria-live="polite" className="min-h-[16rem] whitespace-pre-wrap rounded-2xl bg-[#dfe9e1] p-4 font-mono text-sm text-forest-deep">
                {!session ? t("sim.idle") : ussd.isPending ? t("sim.running") : session.screen}
                {session && english && session.english && !ussd.isPending && (
                  <p className="mt-3 border-t border-forest/20 pt-2 font-sans text-xs text-forest/80">EN: {session.english}</p>
                )}
              </div>
              <div className="mt-4">
                {!session ? (
                  <Button variant="primary" icon={Phone} className="w-full" onClick={dial} loading={ussd.isPending}>{t("sim.dial")}</Button>
                ) : session.ended ? (
                  <div className="flex gap-2">
                    <Button className="flex-1" icon={PhoneOff} onClick={() => setSession(null)}>{t("sim.end")}</Button>
                    <Button variant="primary" className="flex-1" icon={Phone} onClick={dial}>{t("sim.again")}</Button>
                  </div>
                ) : (
                  <form onSubmit={reply} className="flex gap-2">
                    <label className="sr-only" htmlFor="ussd-answer">{t("sim.reply")}</label>
                    <input id="ussd-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} autoFocus autoComplete="off"
                      className="h-10 min-w-0 flex-1 rounded-control border border-white/20 bg-white px-3 text-sm" placeholder={t("sim.reply")} />
                    <Button type="submit" variant="primary" icon={Send} loading={ussd.isPending}>{t("sim.send")}</Button>
                    <Button icon={PhoneOff} onClick={() => setSession(null)} aria-label={t("sim.hangUp")} />
                  </form>
                )}
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("sim.sms")} note={t("sim.smsHint")} />
          <div className="flex h-[24rem] flex-col p-5">
            <ol aria-live="polite" className="flex-1 space-y-2 overflow-y-auto rounded-control bg-canvas p-3">
              {thread.length === 0 && <li className="text-sm text-muted">{t("sim.noSms")}</li>}
              {thread.map((message, index) => (
                <li key={index} className={cx("max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm",
                  message.side === "out" ? "ml-auto bg-primary text-white" : message.side === "error" ? "bg-critical-soft text-critical" : "bg-surface text-ink shadow-sm")}>
                  {message.text}
                </li>
              ))}
            </ol>
            <form onSubmit={submitSms} className="mt-3 flex gap-2">
              <label className="sr-only" htmlFor="sms-text">{t("sim.smsText")}</label>
              <input id="sms-text" value={sms} onChange={(event) => setSms(event.target.value)} maxLength={480} autoComplete="off"
                className="h-10 min-w-0 flex-1 rounded-control border border-line bg-surface px-3 text-sm" placeholder="IMVURA 12" />
              <Button type="submit" variant="primary" icon={MessageSquare} loading={sendSms.isPending}>{t("sim.send")}</Button>
            </form>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title={t("sim.trace")} />
        {trace.length === 0 ? (
          <p className="p-5 text-sm text-muted">{t("sim.noTrace")}</p>
        ) : (
          <ol className="divide-y divide-line">
            {trace.map((item) => (
              <li key={item.id} className="grid gap-1 px-5 py-3 text-sm sm:grid-cols-[6rem_1fr]">
                <span><Badge tone={item.channel === "USSD" ? "brand" : "water"}>{item.channel}</Badge></span>
                <span>
                  <span className="font-mono text-xs text-muted">{item.sent}</span>
                  <span className="block whitespace-pre-wrap">{item.reply}</span>
                  {english && item.english && <span className="block text-xs text-muted">EN: {item.english}</span>}
                  {item.record && <Badge tone="good" className="mt-1">{t("sim.recorded", { type: item.record.replaceAll("_", " ") })}</Badge>}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
