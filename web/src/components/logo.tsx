import Link from "next/link";
import { Leaf } from "lucide-react";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-crop-dark text-white">
        <Leaf className="h-5 w-5" />
      </div>
      <div className="flex flex-col leading-tight">
        <span className="text-sm font-semibold">CropDataSpace</span>
        <span className="text-xs text-muted-foreground">IoT Platform</span>
      </div>
    </Link>
  );
}
