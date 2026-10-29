// Usage (Vince, 2026-10-29): the room is in place before its numbers. The API counts each request's tokens since
// token billing step 1 (request_logs); this page fills in once the usage report and the billing rules are built
// (build plan: steps 2–10). Until then it says what will appear here. Super admins and supervisors (Clients wing).
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import soon from "../kit/coming-soon.module.css";
import styles from "../kit/dashboard.module.css";

export const metadata = { title: "Usage" };

const COMING: { lead: string; text: string }[] = [
  { lead: "This month", text: "tokens in and out per company, app and key" },
  { lead: "Limits", text: "each key's monthly limit and how much is used, with warnings at 80% and 100%" },
  { lead: "Statement", text: "each company's monthly statement, to download as CSV" },
  { lead: "Plans and top-ups", text: "a key's plan, top-ups and pausing a key (super admin, security password)" },
];

export default async function UsagePage() {
  await testersGoToChat(); // testers have only the Chat page

  return (
    <section className={styles.card} aria-labelledby="usage-soon">
      <p className={soon.status}>Coming with token billing</p>
      <h2 id="usage-soon">Usage will show here</h2>
      <p className={styles.muted}>
        The AI service already counts the tokens each request uses. This room fills in once the usage report and the
        billing rules are built.
      </p>
      <ul className={soon.list}>
        {COMING.map((item) => (
          <li key={item.lead}>
            <span className={soon.lead}>{item.lead}</span>
            <span className={styles.muted}>{item.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
