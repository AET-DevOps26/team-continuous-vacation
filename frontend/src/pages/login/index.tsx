import { useLogin, useNotification } from "@refinedev/core";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ensureDemoSession } from "@/providers/auth-provider";
import { useNavigate } from "react-router";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export const LoginPage: React.FC = () => {
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const { open: notify } = useNotification();
  const [demoLoading, setDemoLoading] = useState(false);
  const isPending = loginMutation.status === "pending";

  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const handleDemo = async () => {
    setDemoLoading(true);
    try {
      await ensureDemoSession();
      navigate("/");
      window.location.reload();
    } catch {
      notify?.({
        type: "error",
        message: "Failed to create demo session. Please try again.",
      });
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome to TripTailor</CardTitle>
          <p className="text-muted-foreground text-sm">
            Sign in or try instantly with a demo account
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <Button
            className="w-full"
            variant="default"
            size="lg"
            onClick={handleDemo}
            disabled={demoLoading}
          >
            {demoLoading ? "Creating demo..." : "Try Demo (No Sign-up)"}
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                or sign in
              </span>
            </div>
          </div>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((values) => loginMutation.mutate(values))}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={isPending}>
                Sign In
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
