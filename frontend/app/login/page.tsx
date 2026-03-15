"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Youtube } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, register, isLoading } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      const apiErr = err as { detail?: string; message?: string };
      setError(apiErr?.detail || apiErr?.message || "Błąd logowania");
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Youtube className="h-8 w-8 text-red-500" />
            <span className="text-2xl font-bold text-white">YT Intel OS</span>
          </div>
          <p className="text-gray-400 text-sm">Platforma Automatyzacji YouTube</p>
        </div>

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white text-center">
              {mode === "login" ? "Zaloguj się" : "Utwórz konto"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "register" && (
                <div className="space-y-1">
                  <Label className="text-gray-300">Imię i nazwisko</Label>
                  <Input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Twoje imię"
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
              )}
              <div className="space-y-1">
                <Label className="text-gray-300">Email</Label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ty@przyklad.pl"
                  required
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-gray-300">Hasło</Label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>

              {error && (
                <Alert className="border-red-800 bg-red-900/20">
                  <AlertDescription className="text-red-400">{error}</AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-red-600 hover:bg-red-700"
              >
                {isLoading ? (
                  <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Przetwarzanie...</>
                ) : mode === "login" ? "Zaloguj się" : "Utwórz konto"}
              </Button>

              <p className="text-center text-sm text-gray-400">
                {mode === "login" ? "Nie masz konta?" : "Masz już konto?"}{" "}
                <button
                  type="button"
                  onClick={() => setMode(mode === "login" ? "register" : "login")}
                  className="text-red-400 hover:text-red-300 underline"
                >
                  {mode === "login" ? "Zarejestruj się" : "Zaloguj się"}
                </button>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
