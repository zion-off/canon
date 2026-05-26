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
    <div className="min-h-screen flex flex-col">
      <AppHeader userRole={user.role} />
      <main className="flex-1 px-5">{children}</main>
    </div>
  );
}
