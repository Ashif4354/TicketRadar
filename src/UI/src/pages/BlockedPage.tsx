import React from 'react';
import { Lock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export function BlockedPage() {
  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md border border-destructive/20 shadow-2xl bg-destructive/5 p-6 rounded-2xl text-center space-y-6">
        <CardHeader className="space-y-2 p-0 text-destructive text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-destructive/10 text-destructive shadow-lg mb-2">
            <Lock className="h-7 w-7" />
          </div>
          <CardTitle className="text-2xl font-extrabold tracking-tight">Access Blocked</CardTitle>
          <CardDescription className="text-xs text-destructive-foreground/75">
            You are blocked and cannot access the app content.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Your account has been blocked by an administrator. If you believe this is a mistake, please contact the support desk.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
