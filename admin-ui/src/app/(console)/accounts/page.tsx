import { currentAccount } from "@/lib/session/current-account";

import Placeholder from "../placeholder";

export const metadata = { title: "Accounts" };

export default async function AccountsPage() {
  const me = await currentAccount();
  if (!me.ok || me.data.role !== "super_admin") {
    return (
      <Placeholder title="Accounts" step="Super admin only">
        Only a super admin can see and manage console accounts. (FastAPI refuses these requests for anyone else.)
      </Placeholder>
    );
  }

  return (
    <Placeholder title="Accounts" step="Filled in 6B.4">
      Console accounts: add, reset password, change role, deactivate.
    </Placeholder>
  );
}
