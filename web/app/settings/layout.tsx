'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { User, Shield, Building2, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';

const settingsTabs = [
  { name: 'Profile', href: '/settings', icon: User },
  { name: 'Security', href: '/settings/security', icon: Shield },
  { name: 'Organization', href: '/settings/organization', icon: Building2 },
  { name: 'Notifications', href: '/settings/notifications', icon: Bell },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your account settings and preferences
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {settingsTabs.map((tab) => {
              const isActive =
                tab.href === '/settings'
                  ? pathname === '/settings'
                  : pathname.startsWith(tab.href);
              return (
                <Link
                  key={tab.name}
                  href={tab.href}
                  className={cn(
                    'flex items-center py-4 px-1 border-b-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  <tab.icon className="h-4 w-4 mr-2" />
                  {tab.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="max-w-3xl">{children}</div>
      </div>
    </DashboardLayout>
  );
}
