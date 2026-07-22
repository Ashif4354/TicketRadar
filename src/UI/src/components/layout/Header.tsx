import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Radar, Shield, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { logout } from '../../lib/firebase';
import type { HeaderProps } from '../../types';

export function Header({ user, claims }: HeaderProps) {
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

  const isAdmin = claims?.role === 'admin';

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

        <div className="flex items-center gap-4">
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
                <div className="absolute right-0 mt-2 w-64 rounded-xl border border-border/80 bg-card p-4 shadow-xl glassmorphism text-left animate-in fade-in slide-in-from-top-2 duration-150">
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
            <Link to="/login">
              <Button size="sm" className="h-9 px-4 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer">
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
