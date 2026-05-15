import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useGetIdentity } from "@refinedev/core";

type User = {
  id: string;
  name: string;
};

export function UserAvatar() {
  const { data: user, isLoading } = useGetIdentity<User>();

  if (isLoading || !user) {
    return <Skeleton className={cn("h-9", "w-9", "rounded-full")} />;
  }

  return (
    <Avatar className="h-9 w-9 border border-border">
      <AvatarFallback className="bg-primary/10 text-primary text-sm font-medium">
        {getInitials(user.name)}
      </AvatarFallback>
    </Avatar>
  );
}

const getInitials = (name = "") => {
  const parts = name.trim().split(" ");
  if (parts.length === 0) return "?";
  let initials = parts[0][0]?.toUpperCase() ?? "?";
  if (parts.length > 1) {
    initials += parts[parts.length - 1][0]?.toUpperCase() ?? "";
  }
  return initials;
};
