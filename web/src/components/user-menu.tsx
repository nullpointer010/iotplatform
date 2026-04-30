"use client";

import { useRouter } from "next/navigation";
import { LogOut, User, Languages, Check } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuPortal,
} from "@/components/ui/dropdown-menu";
import { RoleBadge } from "@/components/role-badge";
import { useMe } from "@/lib/auth";

const LOCALE_LABEL: Record<string, string> = { es: "Español", en: "English" };

export function UserMenu() {
  const t = useTranslations("nav");
  const router = useRouter();
  const locale = useLocale();
  const me = useMe();

  const setLocale = (next: string) => {
    document.cookie = `NEXT_LOCALE=${next}; path=/; max-age=31536000; samesite=lax`;
    router.refresh();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          aria-label="User menu"
          className="rounded-full"
        >
          <User className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col gap-1">
            <span>{me.data?.username ?? "…"}</span>
            {me.data ? <RoleBadge roles={me.data.roles} /> : null}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <Languages className="mr-2 h-4 w-4" />
            {t("language")}
          </DropdownMenuSubTrigger>
          <DropdownMenuPortal>
            <DropdownMenuSubContent>
              {(["es", "en"] as const).map((loc) => (
                <DropdownMenuItem
                  key={loc}
                  onSelect={() => setLocale(loc)}
                  className="justify-between"
                >
                  {LOCALE_LABEL[loc]}
                  {locale === loc ? <Check className="h-4 w-4" /> : null}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuPortal>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => {
            window.location.href = "/oauth2/sign_out?rd=/";
          }}
        >
          <LogOut className="mr-2 h-4 w-4" />
          {t("logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
