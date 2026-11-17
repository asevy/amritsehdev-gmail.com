import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { coachMessages } from "@/lib/portal-data";
import { sendCoachMessage } from "@/app/actions/portal";
import { PageHeader, MembershipRequired } from "@/components/portal";
import { Notice } from "@/components/ui";
import { fmtDateTime } from "@/lib/money";
import { SITE } from "@/config/site";

export default async function MessagesPage() {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const msgs = coachMessages(user.id);
  return (
    <>
      <PageHeader eyebrow="Coach messages" title="Your coach">Replies within {SITE.coachResponseSla} during support hours ({SITE.supportHours}).</PageHeader>
      <div className="mb-5">
        <Notice title="Medical questions go to the medical practice">
          Coaches can&apos;t advise on symptoms, medication or test results. Use <Link href="/portal/care#messages" className="underline">Care → Messages</Link> for the clinical team. For emergencies call 911; in crisis call or text 9-8-8.
        </Notice>
      </div>
      <ol className="space-y-3">
        {msgs.map((m) => (
          <li key={m.id} className={`max-w-[80%] rounded-2xl px-4 py-3 ${m.sender_role === "member" ? "ml-auto bg-ink text-paper" : "card"}`}>
            <p className={`text-xs ${m.sender_role === "member" ? "text-paper/60" : "text-muted"}`}>{m.sender_name} · {fmtDateTime(m.created_at)}</p>
            <p className="mt-1 whitespace-pre-wrap text-[15px] leading-6">{m.body}</p>
          </li>
        ))}
      </ol>
      <form action={sendCoachMessage} className="card mt-6 flex items-end gap-3 p-3">
        <label className="flex-1"><span className="sr-only">Message</span><textarea name="body" rows={2} required className="input border-0 focus:ring-0" placeholder="Message your coach…" /></label>
        <button className="btn-primary">Send</button>
      </form>
    </>
  );
}
