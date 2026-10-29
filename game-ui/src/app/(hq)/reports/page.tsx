// Reports (Vince, 2026-10-29): the room is in place before its charts. Performance shows the live traffic (1 h to
// 7 d); Reports will hold the slower, period-based charts for reporting. Which charts is still to be decided, so the
// page lists examples. Super admins and supervisors (Monitor wing).
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import soon from "../kit/coming-soon.module.css";
import styles from "../kit/dashboard.module.css";

export const metadata = { title: "Reports" };

const EXAMPLES: { lead: string; text: string }[] = [
  { lead: "Questions", text: "how many were asked per week and month, per company and app" },
  { lead: "Answers", text: "answered with citations vs. referred to HR, per collection" },
  { lead: "Documents", text: "the files and pages cited most, and the questions nothing answered" },
  { lead: "HR records", text: "which HR lookups are used, per company" },
  { lead: "Export", text: "a period's charts as PDF or CSV" },
];

export default async function ReportsPage() {
  await testersGoToChat(); // testers have only the Chat page

  return (
    <section className={styles.card} aria-labelledby="reports-soon">
      <p className={soon.status}>Coming later</p>
      <h2 id="reports-soon">Reports will show here</h2>
      <p className={styles.muted}>
        Charts over weeks and months, for reporting. Performance keeps the live view of the last hour to week. Which
        charts come first is still to be decided; for example:
      </p>
      <ul className={soon.list}>
        {EXAMPLES.map((item) => (
          <li key={item.lead}>
            <span className={soon.lead}>{item.lead}</span>
            <span className={styles.muted}>{item.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
