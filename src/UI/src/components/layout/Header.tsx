import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Radar, Shield, LogOut, BookOpen, User as UserIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { logout } from '../../lib/firebase';
import { isSecurityDisabled } from '../../utils/security';
import type { HeaderProps } from '../../types';

export function Header({ user, claims, config }: HeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const handleLogout = async () => {
    setDropdownOpen(false);
    await logout();
    navigate('/login');
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const securityDisabled = isSecurityDisabled(config);
  const isAdmin = !securityDisabled && claims?.role === 'admin';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border glassmorphism">
      <div className="container mx-auto max-w-7xl flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20">
            <Radar className="h-5.5 w-5.5" />
          </div>
          <div className="text-left">
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-rose-400 bg-clip-text text-transparent flex items-center gap-1.5">
              TicketRadar
            </span>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider -mt-0.5">
              Movie Ticket Alerts
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          {(user || securityDisabled) && (
            <Link
              to="/app"
              className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground bg-muted/20 hover:bg-muted/50 px-3 py-1.5 rounded-lg border border-border/50 transition-colors"
            >
              <Radar className="h-3.5 w-3.5 text-rose-400" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
          )}

          {isAdmin && (
            <Link
              to="/admin"
              className="flex items-center gap-1.5 text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 rounded-lg border border-rose-500/30 transition-colors"
            >
              <Shield className="h-3.5 w-3.5" />
              <span>Admin Panel</span>
            </Link>
          )}

          <Link
            to="/instructions"
            className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground bg-muted/20 hover:bg-muted/50 px-3 py-1.5 rounded-lg border border-border/50 transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5 text-rose-400" />
            <span className="hidden sm:inline">Instructions</span>
          </Link>

          {securityDisabled && !user && (
            <Link
              to="/profile"
              className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground bg-muted/20 hover:bg-muted/50 px-3 py-1.5 rounded-lg border border-border/50 transition-colors"
            >
              <UserIcon className="h-3.5 w-3.5 text-rose-400" />
              <span className="hidden sm:inline">Profile</span>
            </Link>
          )}

          {user ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 outline-none focus:outline-none cursor-pointer"
              >
                {user.photoURL ? (
                  <img
                    src={user.photoURL}
                    alt={user.displayName || "User profile"}
                    className="h-9 w-9 rounded-full border border-rose-500/30 object-cover shadow-sm hover:border-rose-500/80 transition-colors"
                  />
                ) : (
                  <div className="h-9 w-9 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-500 flex items-center justify-center font-bold text-sm shadow-sm hover:border-rose-500/80 transition-colors">
                    {user.displayName ? user.displayName.charAt(0).toUpperCase() : user.email?.charAt(0).toUpperCase()}
                  </div>
                )}
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl border border-border bg-[#141419] p-4 shadow-2xl text-left animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="flex items-center gap-3 border-b border-border/40 pb-3 mb-3">
                    {user.photoURL ? (
                      <img src={user.photoURL} className="h-10 w-10 rounded-full border border-border" alt="" />
                    ) : (
                      <div className="h-10 w-10 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-sm">
                        {user.displayName ? user.displayName.charAt(0).toUpperCase() : "U"}
                      </div>
                    )}
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-foreground truncate">{user.displayName || "User"}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {claims?.authorized && (
                      <div className="flex items-center justify-between text-xs py-1 border-b border-border/40 pb-2">
                        <span className="text-muted-foreground">Status:</span>
                        <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">
                          AUTHORIZED
                        </Badge>
                      </div>
                    )}

                    {isAdmin && (
                      <Link
                        to="/admin"
                        onClick={() => setDropdownOpen(false)}
                        className="flex w-full items-center gap-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/25 text-rose-400 text-xs font-semibold px-3 py-2 border border-rose-500/20 transition-colors cursor-pointer justify-center"
                      >
                        <Shield className="h-3.5 w-3.5" />
                        Admin Panel
                      </Link>
                    )}

                    <Link
                      to="/profile"
                      onClick={() => setDropdownOpen(false)}
                      className="flex w-full items-center gap-2 rounded-lg bg-muted/30 hover:bg-muted/60 text-foreground text-xs font-medium px-3 py-2 border border-border/40 transition-colors cursor-pointer"
                    >
                      <UserIcon className="h-3.5 w-3.5 text-rose-400" />
                      Profile & Channels
                    </Link>

                    <Button
                      onClick={handleLogout}
                      variant="outline"
                      className="w-full text-xs font-semibold h-9 flex items-center justify-center gap-2 hover:bg-rose-500/10 hover:text-rose-400 border-border hover:border-rose-500/20"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Log Out
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {securityDisabled ? (
                <Badge className="hidden sm:inline-flex bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] font-bold px-2 py-0.5 rounded-full">
                  NO AUTH
                </Badge>
              ) : (
                <Link to="/login">
                  <Button size="sm" className="h-9 px-4 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer">
                    Sign In
                  </Button>
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
