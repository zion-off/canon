import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/actions/auth";
import { AppHeader } from "@/components/layout/AppHeader";
import { ROUTE_LOGOUT } from "@/lib/constants";

export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getCurrentUser();

  if (!user) {
    redirect(ROUTE_LOGOUT);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader userRole={user.role} />
      <main className="flex flex-1 flex-col px-5">{children}</main>
    </div>
  );
}
