import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/actions/auth";
import { AppHeader } from "@/components/layout/AppHeader";
import { ROUTE_LOGIN } from "@/lib/constants";

export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getCurrentUser();

  if (!user) {
    redirect(ROUTE_LOGIN);
  }

  return (
    <div className="min-h-screen bg-canon-bg">
      <AppHeader user={{ name: user.name, email: user.email, role: user.role }} />
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
