/**
 * Cart link in the top bar, showing how many items are in the cart.
 */
"use client";
import Link from "next/link";
import { useCart } from "../lib/cart";

export function CartBadge() {
  const { count } = useCart();
  return (
    <Link href="/shop/cart" className="btn secondary">
      Cart{count > 0 ? ` · ${count}` : ""}
    </Link>
  );
}
