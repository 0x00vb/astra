"use client";

import Link from "next/link";
import { User, LogIn, UserPlus, LogOut, BarChart3 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { logout } from "../lib/api";

export default function Navbar() {
  const { isAuthenticated, user } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-black">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo/Brand */}
          <Link href="/" className="flex items-center gap-2">
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
              Astra
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  href="/analytics"
                  className="flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  <BarChart3 className="h-4 w-4" />
                  <span className="hidden sm:inline">Analytics</span>
                </Link>
                <div className="flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">
                    {user?.full_name || user?.email || "Usuario"}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Salir</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  <LogIn className="h-4 w-4" />
                  <span className="hidden sm:inline">Iniciar Sesión</span>
                </Link>
                <Link
                  href="/register"
                  className="flex items-center gap-2 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
                >
                  <UserPlus className="h-4 w-4" />
                  <span className="hidden sm:inline">Registrarse</span>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

