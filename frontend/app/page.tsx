import { redirect } from "next/navigation";
import { ROUTE_DASHBOARD } from "@/lib/constants";

export default function Home() {
  redirect(ROUTE_DASHBOARD);
}
