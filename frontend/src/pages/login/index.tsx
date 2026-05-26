import { useLogin, useRegister, useNotification } from "@refinedev/core";
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

const authSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type AuthFormValues = z.infer<typeof authSchema>;

export const LoginPage: React.FC = () => {
  const loginMutation = useLogin();
  const registerMutation = useRegister();
  const navigate = useNavigate();
  const { open: notify } = useNotification();
  const [demoLoading, setDemoLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const form = useForm<AuthFormValues>({
    resolver: zodResolver(authSchema),
    defaultValues: { email: "", password: "" },
  });

  const handleSubmit = (values: AuthFormValues) => {
    if (mode === "login") {
      loginMutation.mutate(values);
    } else {
      registerMutation.mutate(values);
    }
  };

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

  const isPending =
    loginMutation.status === "pending" || registerMutation.status === "pending";

  return (
    <div className="flex items-center justify-center min-h-screen p-4 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome to TripTailor</CardTitle>
          <p className="text-muted-foreground text-sm">
            AI-powered travel itineraries, tailored to your vibe.
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
              <span className="bg-card px-2 text-muted-foreground">
                or {mode === "login" ? "sign in" : "create account"}
              </span>
            </div>
          </div>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="you@example.com"
                        {...field}
                      />
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
                      <Input
                        type="password"
                        placeholder="Min. 8 characters"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending
                  ? mode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                  : mode === "login"
                    ? "Sign In"
                    : "Create Account"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-sm text-muted-foreground">
            {mode === "login" ? (
              <>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline font-medium"
                  onClick={() => setMode("register")}
                >
                  Register
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline font-medium"
                  onClick={() => setMode("login")}
                >
                  Sign in
                </button>
              </>
            )}
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
