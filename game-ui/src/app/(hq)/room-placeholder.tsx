import styles from "./hq.module.css";

// What a room shows until its real page is built (G3 onward). The panel header above it already names the room.
export default function RoomPlaceholder() {
  return (
    <section className={styles.placeholder}>
      <p>
        <strong>This room isn&apos;t connected yet.</strong>
      </p>
      <p>
        Its data comes in a later step, one room at a time. Until then, use the same page in the ITI AI Console
        (admin-ui).
      </p>
    </section>
  );
}
