"use client";

import { useActionState, useState } from "react";

import { logIn, type LoginState } from "@/lib/session/actions";

import styles from "./login.module.css";

const start: LoginState = { error: null, username: "" };

export default function LoginForm() {
  const [state, action, pending] = useActionState(logIn, start);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  // Caps Lock: read from any key press in the password box (the browser knows it; there is no event for it)
  const checkCaps = (e: React.KeyboardEvent<HTMLInputElement>) => setCapsLock(e.getModifierState("CapsLock"));

  return (
    <form action={action} className={styles.form}>
      <h2>Sign in to the console</h2>
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
      <div className={styles.field}>
        <label htmlFor="password">Password</label>
        <div className={styles.passwordRow}>
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
            aria-describedby={capsLock ? "caps-lock" : undefined}
            onKeyDown={checkCaps}
            onKeyUp={checkCaps}
            onBlur={() => setCapsLock(false)}
          />
          {/* shows the typed password (for checking it); aria-pressed tells screen readers which state it is in */}
          <button
            type="button"
            className={styles.reveal}
            aria-pressed={showPassword}
            aria-controls="password"
            onClick={() => setShowPassword((v) => !v)}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        {capsLock && (
          <p id="caps-lock" role="status" className={styles.caps}>
            ▲ Caps Lock is on
          </p>
        )}
      </div>
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
