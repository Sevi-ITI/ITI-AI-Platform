// Which console this is. admin-ui and game-ui share src/lib/api and src/lib/session as exact copies; only this
// file differs. Browsers share cookies across ports on the same host, so each console has its own session
// cookie: logging in or out of one never touches the other.

export const SESSION_COOKIE = "iti_game_session";
