export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="min-h-screen bg-[#080810] flex items-center justify-center">
      {children}
    </div>
  );
}
