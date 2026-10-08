"use client";

import { useActionState } from "react";

import { logIn, type LoginState } from "@/lib/session/actions";

import styles from "./login.module.css";

const start: LoginState = { error: null, username: "" };

export default function LoginForm() {
  const [state, action, pending] = useActionState(logIn, start);

  return (
    <form action={action} className={styles.form}>
      <h2>Log in</h2>
      <label className={styles.field}>
        <span>Username</span>
        <input
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          defaultValue={state.username}
          required
          autoFocus
        />
      </label>
      <label className={styles.field}>
        <span>Password</span>
        <input name="password" type="password" autoComplete="current-password" required />
      </label>
      {state.error && (
        <p role="alert" className={styles.error}>
          ✕ {state.error}
        </p>
      )}
      <button type="submit" className={styles.button} disabled={pending} aria-busy={pending}>
        {pending && <span className={styles.spinner} aria-hidden="true" />}
        Log in
      </button>
    </form>
  );
}
