'use client';

import { useState } from 'react';
import { Loader2, CheckCircle, Bell, Mail, MessageSquare } from 'lucide-react';

interface NotificationSetting {
  id: string;
  label: string;
  description: string;
  email: boolean;
  inApp: boolean;
}

const defaultNotifications: NotificationSetting[] = [
  {
    id: 'deadline_reminder',
    label: 'Deadline Reminders',
    description: 'Get notified before deadlines are due',
    email: true,
    inApp: true,
  },
  {
    id: 'deadline_overdue',
    label: 'Overdue Deadlines',
    description: 'Alert when a deadline becomes overdue',
    email: true,
    inApp: true,
  },
  {
    id: 'document_uploaded',
    label: 'Document Uploads',
    description: 'Notification when documents are uploaded to your transactions',
    email: false,
    inApp: true,
  },
  {
    id: 'document_review',
    label: 'Documents Needing Review',
    description: 'Alert when extracted documents need verification',
    email: true,
    inApp: true,
  },
  {
    id: 'transaction_update',
    label: 'Transaction Updates',
    description: 'Changes to transaction status or details',
    email: false,
    inApp: true,
  },
  {
    id: 'closing_reminder',
    label: 'Closing Reminders',
    description: 'Reminder as closing date approaches',
    email: true,
    inApp: true,
  },
  {
    id: 'compliance_alert',
    label: 'Compliance Alerts',
    description: 'Statutory deadline and compliance warnings',
    email: true,
    inApp: true,
  },
  {
    id: 'weekly_summary',
    label: 'Weekly Summary',
    description: 'Weekly digest of all transaction activity',
    email: true,
    inApp: false,
  },
];

export default function NotificationSettingsPage() {
  const [notifications, setNotifications] = useState<NotificationSetting[]>(defaultNotifications);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const toggleNotification = (id: string, type: 'email' | 'inApp') => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, [type]: !n[type] } : n
      )
    );
    setSaved(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // API call would go here
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSaved(true);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Notification Preferences */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center">
            <Bell className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Notification Preferences</h2>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Choose how you want to be notified about updates and alerts
          </p>
        </div>

        <div className="p-6">
          {/* Column Headers */}
          <div className="flex items-center justify-end space-x-8 mb-4 pr-2">
            <div className="flex items-center text-sm font-medium text-gray-500">
              <Mail className="h-4 w-4 mr-1" />
              Email
            </div>
            <div className="flex items-center text-sm font-medium text-gray-500">
              <MessageSquare className="h-4 w-4 mr-1" />
              In-App
            </div>
          </div>

          {/* Notification Items */}
          <div className="space-y-4">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {notification.label}
                  </p>
                  <p className="text-sm text-gray-500">{notification.description}</p>
                </div>
                <div className="flex items-center space-x-8">
                  <button
                    type="button"
                    onClick={() => toggleNotification(notification.id, 'email')}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                      notification.email ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                    role="switch"
                    aria-checked={notification.email}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        notification.email ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleNotification(notification.id, 'inApp')}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                      notification.inApp ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                    role="switch"
                    aria-checked={notification.inApp}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        notification.inApp ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-gray-200 mt-6">
            <div>
              {saved && (
                <div className="flex items-center text-sm text-green-600">
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Preferences saved
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Preferences'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Email Preferences */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Email Settings</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Email Digest Frequency</p>
              <p className="text-sm text-gray-500">How often to receive email summaries</p>
            </div>
            <select className="rounded-md border-gray-300 text-sm focus:border-primary-500 focus:ring-primary-500">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="never">Never</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Deadline Reminder Timing</p>
              <p className="text-sm text-gray-500">When to send deadline reminders</p>
            </div>
            <select className="rounded-md border-gray-300 text-sm focus:border-primary-500 focus:ring-primary-500">
              <option value="1">1 day before</option>
              <option value="3">3 days before</option>
              <option value="7">7 days before</option>
            </select>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h3 className="text-sm font-medium text-blue-800">About Notifications</h3>
        <p className="mt-2 text-sm text-blue-700">
          Email notifications are sent to your registered email address. In-app notifications
          appear in the notification center (coming soon). Critical compliance alerts are
          always sent regardless of preferences.
        </p>
      </div>
    </div>
  );
}
