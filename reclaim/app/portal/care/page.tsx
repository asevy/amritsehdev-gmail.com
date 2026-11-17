import Link from "next/link";
import { requireUser } from "@/lib/auth";
import {
  getEnrolment, listEncounters, listPrescriptions, listLabs, listClinicalMessages, presentPharmacyOptions,
} from "@/lib/clinical";
import { patientPharmacyView, fillsUsed } from "@/lib/pharmacy";
import { currentConsents } from "@/lib/consent";
import {
  submitIntake, bookVisit, cancelVisit, choosePharmacyAction, requestFillAction, payFillAction, sendClinicalMessageAction, reportSideEffectAction,
} from "@/app/actions/care";
import { PHARMACY_OPTIONS } from "@/config/partners";
import { ENTITIES } from "@/config/site";
import { CLINICAL_ACKS } from "@/config/consents";
import { PageHeader, Panel, Flash } from "@/components/portal";
import { EntityTag, EmergencyNotice, Notice } from "@/components/ui";
import { cadExact, fmtDate, fmtDateTime } from "@/lib/money";

function visitSlots(): string[] {
  const out: string[] = [];
  for (let day = 2; day <= 9 && out.length < 6; day++) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() + day);
    if ([0, 6].includes(d.getUTCDay())) continue;
    for (const h of [14, 20]) { const s = new Date(d); s.setUTCHours(h, 0, 0, 0); out.push(s.toISOString()); }
  }
  return out.slice(0, 6);
}

const FILL_STATUS: Record<string, string> = {
  requested: "Waiting for pharmacist review", verified: "Verified", awaiting_payment: "Ready — pay the pharmacy to release", paid: "Paid — being prepared",
  shipped: "Shipped", delivered: "Delivered", cancelled: "Cancelled",
};

function YesNo({ name, label }: { name: string; label: string }) {
  return (
    <fieldset className="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3 text-sm">
      <legend className="sr-only">{label}</legend>
      <span className="max-w-lg">{label}</span>
      <span className="flex gap-4">
        <label className="flex items-center gap-1.5"><input type="radio" name={name} value="yes" required className="accent-ink" /> Yes</label>
        <label className="flex items-center gap-1.5"><input type="radio" name={name} value="no" className="accent-ink" /> No</label>
      </span>
    </fieldset>
  );
}

export default async function CarePage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const user = await requireUser(["member"]);
  const sp = await searchParams;
  const clinic = ENTITIES.clinical;
  const enrol = getEnrolment(user);
  const header = (
    <PageHeader eyebrow={<EntityTag entity="clinical" label={`Provided by ${clinic.displayName}`} />} title="Care & prescriptions">
      This area is operated for the independent medical practice. Your medical record is held by the practice; RECLAIM coaches and staff can&apos;t see it.
    </PageHeader>
  );

  if (sp.urgent) {
    return (
      <>{header}
        <EmergencyNotice />
        <div className="mt-5"><Notice tone="clinical" title="Please don't wait for a virtual visit">Something in your answers means you should be seen in person promptly. If you have chest pain, fainting or severe shortness of breath, call 911 now. Otherwise contact your family doctor or a walk-in clinic today. The practice has been notified.</Notice></div>
      </>
    );
  }

  if (!enrol) {
    if (!sp.start) {
      return (
        <>{header}
          <Panel title="Request a medical assessment">
            <p className="text-sm leading-6 text-ink-2">A physician or nurse practitioner licensed in Ontario reviews your health history and talks with you about options. They decide whether any test or treatment is appropriate. No membership is needed and OHIP-insured services are never charged to you.</p>
            <Link href="/portal/care?start=1" className="btn-primary mt-5">Start the health questionnaire</Link>
          </Panel>
          <div className="mt-5"><EmergencyNotice /></div>
        </>
      );
    }
    return (
      <>{header}
        {sp.error === "ack" && <Flash tone="err">Please confirm all three acknowledgements.</Flash>}
        <form action={submitIntake} className="space-y-5">
          <Panel title="1 · About you">
            <div className="grid gap-4 sm:grid-cols-3">
              <label className="text-sm"><span className="field-label">Legal name</span><input name="legal_name" defaultValue={user.name} required className="input" /></label>
              <label className="text-sm"><span className="field-label">Date of birth</span><input name="dob" type="date" required className="input" /></label>
              <label className="text-sm"><span className="field-label">Ontario health card — last 4 digits</span><input name="hcn_last4" inputMode="numeric" maxLength={4} className="input" /><span className="field-hint">Prototype collects only the last 4 digits. Lets the practice bill OHIP so insured care costs you nothing.</span></label>
            </div>
            <label className="mt-4 block max-w-xs text-sm"><span className="field-label">Age</span>
              <select name="age_band" required className="input"><option value="">Select</option><option value="under18">Under 18</option><option value="18_39">18–39</option><option value="40_64">40–64</option><option value="65plus">65 or older</option></select>
            </label>
          </Panel>
          <Panel title="2 · Safety questions">
            <p className="mb-2 text-xs text-muted">Clinical content placeholder — final questions are set by the practice&apos;s medical director.</p>
            <YesNo name="current_symptoms" label="Do you have chest pain, fainting, or severe shortness of breath right now or in the last 24 hours?" />
            <YesNo name="pregnancy" label="Are you pregnant, breastfeeding, or planning pregnancy in the next 6 months?" />
            <YesNo name="eating_disorder" label="Have you ever been diagnosed with or treated for an eating disorder?" />
            <YesNo name="thyroid_history" label="Do you or a close family member have a history of medullary thyroid cancer or MEN2?" />
            <YesNo name="pancreatitis" label="Have you ever had pancreatitis?" />
            <label className="mt-3 block max-w-xs text-sm"><span className="field-label">Diabetes</span>
              <select name="diabetes_type" className="input"><option value="none">No</option><option value="type2">Type 2</option><option value="type1">Type 1</option><option value="unsure">Not sure</option></select>
            </label>
          </Panel>
          <Panel title="3 · Medications, allergies and what you'd like from the visit">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm"><span className="field-label">Current medications and supplements</span><textarea name="medications" rows={3} className="input" /></label>
              <label className="text-sm"><span className="field-label">Allergies</span><textarea name="allergies" rows={3} className="input" /></label>
              <label className="text-sm sm:col-span-2"><span className="field-label">What would you like to discuss?</span><textarea name="visit_goals" rows={3} className="input" /></label>
            </div>
          </Panel>
          <Panel title="4 · Before you submit">
            <div className="space-y-3 text-sm leading-6">
              {([["ack_privacy", CLINICAL_ACKS.privacy_notice, "/legal/clinical-privacy"], ["ack_virtual", CLINICAL_ACKS.virtual_care, null], ["ack_independence", CLINICAL_ACKS.independence, null]] as const).map(([n, t, href]) => (
                <label key={n} className="flex items-start gap-3"><input type="checkbox" name={n} required className="mt-1 size-4 accent-ink" /><span>{t} {href && <Link href={href} className="underline" target="_blank">Read</Link>}</span></label>
              ))}
            </div>
            <button className="btn-primary mt-5">Send to the medical practice</button>
            <p className="mt-2 text-xs text-muted">Sent only to {clinic.displayName}. Not visible to your coach.</p>
          </Panel>
        </form>
      </>
    );
  }

  const encounters = listEncounters(user);
  const upcoming = encounters.filter((e) => e.status === "booked");
  const rxs = listPrescriptions(user);
  const labs = listLabs(user);
  const msgs = listClinicalMessages(user);
  const pharm = patientPharmacyView(user);
  const consents = currentConsents(user.id);
  const presented = presentPharmacyOptions();

  return (
    <>
      {header}
      {sp.submitted && <Flash>Questionnaire sent to the practice. Book your visit below.</Flash>}
      {sp.booked && <Flash>Visit booked.</Flash>}
      {sp.chosen && <Flash>Pharmacy choice saved and the prescription has been sent.</Flash>}
      {sp.filled && <Flash>Fill requested. A pharmacist will review it and show you the price before you pay.</Flash>}
      {sp.paid && <Flash>Paid to the pharmacy. You&apos;ll get tracking when it ships.</Flash>}
      {sp.reported && <Flash tone={sp.reported === "severe" ? "err" : "ok"}>{sp.reported === "severe" ? "Sent. For severe symptoms don't wait for a reply — call 911 or go to an emergency department." : "Sent to the clinical team. They'll respond within 2 business days."}</Flash>}
      {sp.error && sp.error !== "ack" && <Flash tone="err">{sp.error}</Flash>}

      <div className="mb-5"><EmergencyNotice /></div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title={<span id="visits">Visits</span>}>
          <ul className="divide-y divide-line text-sm">
            {encounters.slice(0, 5).map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 py-2.5">
                <span><span className="font-medium">{e.kind === "initial" ? "Assessment" : "Follow-up"}</span> · {e.clinician_name}, {e.designation}<span className="block text-muted">{fmtDateTime(e.starts_at)} · {e.modality} · {e.status}</span></span>
                <span className="text-right text-xs">
                  {e.insured_status === "ohip" ? <span className="chip border-moss/30 bg-moss-soft text-moss">OHIP · $0</span> : <span className="chip border-line-2 text-muted">Fee confirmed before visit</span>}
                  {e.status === "booked" && <form action={cancelVisit} className="mt-1"><input type="hidden" name="id" value={e.id} /><button className="underline">Cancel</button></form>}
                </span>
              </li>
            ))}
          </ul>
          {upcoming.length === 0 && (
            <form action={bookVisit} className="mt-4 space-y-3 rounded-xl bg-bone/60 p-4">
              <p className="text-sm font-semibold">Book a visit</p>
              <div className="flex flex-wrap gap-2">
                <select name="startsAt" className="input max-w-60">{visitSlots().map((s) => <option key={s} value={s}>{fmtDateTime(s)}</option>)}</select>
                <select name="modality" className="input max-w-32"><option value="video">Video</option><option value="phone">Phone</option></select>
              </div>
              <label className="flex items-start gap-2 text-sm"><input type="checkbox" name="attest" required className="mt-1 accent-ink" /> I will be physically in Ontario at the time of the visit.</label>
              <button className="btn-primary btn-sm">Book</button>
            </form>
          )}
        </Panel>

        <Panel title="Labs">
          {labs.length === 0 ? <p className="text-sm text-muted">No tests ordered.</p> : (
            <ul className="space-y-3 text-sm">{labs.map((l) => (
              <li key={l.id} className="rounded-xl border border-line p-3">
                <p className="font-medium">{l.panel}</p>
                <p className="text-muted">{l.status === "resulted" ? `Resulted ${fmtDate(l.resulted_at)}` : `Requisition issued ${fmtDate(l.ordered_at)} — take it to any community lab`}</p>
                {l.result_summary && <p className="mt-1 text-ink-2">{l.result_summary}</p>}
                {l.clinician_comment && <p className="mt-1 text-ink-2"><span className="font-medium">Clinician:</span> {l.clinician_comment}</p>}
              </li>
            ))}</ul>
          )}
        </Panel>
      </div>

      <section id="prescriptions" className="mt-5 scroll-mt-6">
        <Panel title="Prescriptions">
          {rxs.length === 0 && <p className="text-sm text-muted">No prescriptions. Many people&apos;s plan is the programme alone — that&apos;s the clinician&apos;s call, made with you.</p>}
          <div className="space-y-5">
            {rxs.map((rx) => {
              const inbox = pharm.inbox.find((i) => i.prescription_id === rx.id);
              const fills = inbox ? pharm.fills.filter((f) => f.rx_id === inbox.id) : [];
              const openFill = fills.find((f) => ["requested", "verified", "awaiting_payment", "paid"].includes(f.status));
              const used = inbox ? fillsUsed(inbox.id) : 0;
              return (
                <div key={rx.id} className="rounded-2xl border border-line p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold">{rx.display_name}</p>
                      <p className="text-sm text-ink-2">{rx.sig} · {rx.quantity} · {rx.refills} refill{rx.refills === 1 ? "" : "s"}</p>
                      <p className="mt-1 text-xs text-muted">Prescribed by {rx.clinician_name} on {fmtDate(rx.created_at)} · Monitoring: {rx.monitoring}</p>
                    </div>
                    <EntityTag entity="clinical" label="Prescription" />
                  </div>

                  {!rx.destination_type ? (
                    <form action={choosePharmacyAction} className="mt-5">
                      <input type="hidden" name="rxId" value={rx.id} />
                      <input type="hidden" name="presented" value={presented.join(",")} />
                      <fieldset>
                        <legend className="font-semibold">Where would you like to fill this?</legend>
                        <p className="mt-1 text-sm text-ink-2">You can use any pharmacy. Options are shown in random order and none is pre-selected.</p>
                        <div className="mt-3 grid gap-3">
                          {presented.map((id) => {
                            const o = PHARMACY_OPTIONS.find((x) => x.id === id)!;
                            return (
                              <label key={id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-card p-4 has-checked:border-ink has-checked:ring-1 has-checked:ring-ink">
                                <input type="radio" name="choice" value={id} required className="mt-1 accent-ink" />
                                <span className="text-sm">
                                  <span className="font-semibold">{o.title}</span>
                                  <span className="mt-0.5 block text-ink-2">{o.detail}</span>
                                  {o.disclosure && <span className="mt-2 block rounded-lg bg-warn-soft/60 p-2 text-xs leading-5">{o.disclosure}</span>}
                                  {id === "other_pharmacy" && <input name="detail" placeholder="Pharmacy name, phone or fax" className="input mt-2" />}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </fieldset>
                      <button className="btn-primary mt-4">Confirm my choice</button>
                    </form>
                  ) : rx.destination_type === "aligned_pharmacy" && inbox ? (
                    <div className="mt-5 rounded-xl border border-rx/25 bg-rx-soft/30 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold">Filled by {ENTITIES.pharmacy.legalName}</p>
                        <EntityTag entity="pharmacy" label="Sold by the pharmacy" />
                      </div>
                      <p className="mt-1 text-xs text-muted">Fills used: {used} of {inbox.refills_authorised + 1}. Prices come from the pharmacy and never depend on your membership.</p>
                      {fills.length > 0 && (
                        <ul className="mt-3 space-y-3">
                          {fills.map((f) => (
                            <li key={f.id} className="rounded-lg bg-card p-3 text-sm">
                              <p className="font-medium">{FILL_STATUS[f.status]}</p>
                              <p className="text-xs text-muted">Requested {fmtDate(f.requested_at)}{f.counselled_at ? ` · pharmacist counselling ${fmtDate(f.counselled_at)}` : ""}{f.tracking ? ` · tracking ${f.tracking}` : ""}</p>
                              {f.status === "awaiting_payment" && f.patient_total_cents != null && (
                                <form action={payFillAction} className="mt-3">
                                  <input type="hidden" name="fillId" value={f.id} />
                                  <table className="w-full max-w-sm text-xs">
                                    <tbody>
                                      <tr><td>Medication</td><td className="text-right tabular-nums">{cadExact(f.drug_cents ?? 0)}</td></tr>
                                      <tr><td>Dispensing fee</td><td className="text-right tabular-nums">{cadExact(f.dispensing_fee_cents ?? 0)}</td></tr>
                                      <tr><td>Drug plan pays</td><td className="text-right tabular-nums">−{cadExact(f.plan_pays_cents)}</td></tr>
                                      <tr><td>Delivery {f.delivery_cents ? "(refrigerated)" : ""}</td><td className="text-right tabular-nums">{cadExact(f.delivery_cents ?? 0)}</td></tr>
                                      <tr><td>GST/HST</td><td className="text-right tabular-nums">$0.00 (zero-rated)</td></tr>
                                      <tr className="border-t border-line font-semibold"><td className="pt-1">You pay the pharmacy</td><td className="pt-1 text-right tabular-nums">{cadExact(f.patient_total_cents)}</td></tr>
                                    </tbody>
                                  </table>
                                  <button className="btn-primary btn-sm mt-3">Pay pharmacy (test mode)</button>
                                </form>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                      {!openFill && used <= inbox.refills_authorised && (
                        <form action={requestFillAction} className="mt-3"><input type="hidden" name="rxId" value={inbox.id} /><button className="btn-ghost btn-sm">{fills.length ? "Request refill" : "Request first fill"}</button></form>
                      )}
                    </div>
                  ) : (
                    <p className="mt-4 rounded-lg bg-bone/60 p-3 text-sm">{rx.destination_type === "other_pharmacy" ? `Sent to: ${rx.destination_detail}` : "Paper copy requested — the practice will provide it."} Chosen {fmtDate(rx.choice_made_at)}.</p>
                  )}
                </div>
              );
            })}
          </div>
        </Panel>
      </section>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Panel title={<span id="messages">Messages with the clinical team</span>}>
          <ol className="max-h-80 space-y-2 overflow-y-auto">
            {msgs.map((m) => (
              <li key={m.id} className={`rounded-xl px-3 py-2 text-sm ${m.sender === "patient" ? "ml-8 bg-ink text-paper" : "mr-8 bg-clinic-soft"}`}>
                <p className={`text-xs ${m.sender === "patient" ? "text-paper/60" : "text-muted"}`}>{m.sender_name} · {fmtDateTime(m.created_at)}</p>
                <p className="mt-0.5 whitespace-pre-wrap">{m.body}</p>
              </li>
            ))}
          </ol>
          <form action={sendClinicalMessageAction} className="mt-3 flex gap-2">
            <label className="flex-1"><span className="sr-only">Message</span><textarea name="body" rows={2} required className="input" placeholder="Non-urgent message to the clinical team" /></label>
            <button className="btn-primary btn-sm self-end">Send</button>
          </form>
          <p className="mt-2 text-xs text-muted">Becomes part of your medical record. Replies within 2 business days.</p>
        </Panel>

        <Panel title={<span id="report">Report a side effect or new symptom</span>}>
          <form action={reportSideEffectAction} className="space-y-3">
            <textarea name="description" rows={3} required className="input" placeholder="What happened, when it started, anything that makes it better or worse" />
            <fieldset className="flex flex-wrap gap-4 text-sm"><legend className="field-label">How bad is it?</legend>
              {["mild", "moderate", "severe"].map((s) => <label key={s} className="flex items-center gap-1.5 capitalize"><input type="radio" name="severity" value={s} required className="accent-ink" />{s}</label>)}
            </fieldset>
            <button className="btn-primary btn-sm">Send to clinical team</button>
            <p className="text-xs text-muted">Goes to the medical practice, not your coach. Severe symptoms: call 911.</p>
          </form>
        </Panel>
      </div>

      <Panel title="Sharing between your clinician and coach" className="mt-5">
        <ul className="space-y-2 text-sm">
          <li>Coaching data → clinical team: <strong>{consents.coaching_to_clinical ? "On" : "Off"}</strong></li>
          <li>Care summary → coach: <strong>{consents.clinical_summary_to_coach ? "On" : "Off"}</strong></li>
        </ul>
        <Link href="/portal/privacy" className="mt-3 inline-block text-sm underline">Change in Privacy & data</Link>
      </Panel>
    </>
  );
}
