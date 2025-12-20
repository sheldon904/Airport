'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useDeadlines, useCompleteDeadline, useWaiveDeadline, useExtendDeadline } from '@/hooks';
import {
  Clock,
  CheckCircle,
  AlertTriangle,
  Calendar,
  ChevronRight,
  Filter,
  Loader2,
  X,
  CalendarPlus,
  Ban,
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { formatDate, formatAddress } from '@/lib/utils';

const statusOptions = [
  { value: '', label: 'All Deadlines' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'waived', label: 'Waived' },
  { value: 'extended', label: 'Extended' },
];

function DeadlineRow({
  deadline,
  onComplete,
  onWaive,
  onExtend,
  isActioning,
}: {
  deadline: any;
  onComplete: () => void;
  onWaive: (reason: string) => void;
  onExtend: (newDate: string, reason: string) => void;
  isActioning: boolean;
}) {
  const [showActions, setShowActions] = useState(false);
  const [showWaiveModal, setShowWaiveModal] = useState(false);
  const [showExtendModal, setShowExtendModal] = useState(false);
  const [waiveReason, setWaiveReason] = useState('');
  const [extendDate, setExtendDate] = useState('');
  const [extendReason, setExtendReason] = useState('');

  const isOverdue = new Date(deadline.due_date) < new Date() && deadline.status === 'pending';
  const isPending = deadline.status === 'pending';
  const daysUntilDue = Math.ceil(
    (new Date(deadline.due_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
  );

  const handleWaive = () => {
    if (waiveReason.trim()) {
      onWaive(waiveReason);
      setShowWaiveModal(false);
      setWaiveReason('');
    }
  };

  const handleExtend = () => {
    if (extendDate && extendReason.trim()) {
      onExtend(extendDate, extendReason);
      setShowExtendModal(false);
      setExtendDate('');
      setExtendReason('');
    }
  };

  return (
    <>
      <div
        className={`p-4 hover:bg-gray-50 transition-colors ${
          isOverdue ? 'bg-red-50' : ''
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div
              className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
                isOverdue
                  ? 'bg-red-100'
                  : isPending
                  ? daysUntilDue <= 3
                    ? 'bg-yellow-100'
                    : 'bg-blue-100'
                  : 'bg-green-100'
              }`}
            >
              {deadline.status === 'completed' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : isOverdue ? (
                <AlertTriangle className="h-5 w-5 text-red-600" />
              ) : (
                <Clock
                  className={`h-5 w-5 ${
                    daysUntilDue <= 3 ? 'text-yellow-600' : 'text-blue-600'
                  }`}
                />
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{deadline.title}</p>
              <div className="flex items-center space-x-2 mt-1">
                {deadline.transaction && (
                  <Link
                    href={`/transactions/${deadline.transaction.id}`}
                    className="text-xs text-primary-600 hover:text-primary-500"
                  >
                    {formatAddress(deadline.transaction.property_address)}
                  </Link>
                )}
                {deadline.is_statutory && (
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                    Statutory
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p
                className={`text-sm font-medium ${
                  isOverdue
                    ? 'text-red-600'
                    : daysUntilDue <= 3 && isPending
                    ? 'text-yellow-600'
                    : 'text-gray-900'
                }`}
              >
                {formatDate(deadline.due_date)}
              </p>
              {isPending && (
                <p
                  className={`text-xs ${
                    isOverdue
                      ? 'text-red-500'
                      : daysUntilDue <= 3
                      ? 'text-yellow-500'
                      : 'text-gray-500'
                  }`}
                >
                  {isOverdue
                    ? `${Math.abs(daysUntilDue)} days overdue`
                    : daysUntilDue === 0
                    ? 'Due today'
                    : daysUntilDue === 1
                    ? 'Due tomorrow'
                    : `${daysUntilDue} days left`}
                </p>
              )}
            </div>
            {isPending && (
              <div className="relative">
                <button
                  onClick={() => setShowActions(!showActions)}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                >
                  <ChevronRight
                    className={`h-5 w-5 transition-transform ${
                      showActions ? 'rotate-90' : ''
                    }`}
                  />
                </button>
                {showActions && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border z-10">
                    <button
                      onClick={() => {
                        onComplete();
                        setShowActions(false);
                      }}
                      disabled={isActioning}
                      className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                      Mark Complete
                    </button>
                    <button
                      onClick={() => {
                        setShowExtendModal(true);
                        setShowActions(false);
                      }}
                      className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <CalendarPlus className="h-4 w-4 mr-2 text-blue-500" />
                      Extend Deadline
                    </button>
                    <button
                      onClick={() => {
                        setShowWaiveModal(true);
                        setShowActions(false);
                      }}
                      className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <Ban className="h-4 w-4 mr-2 text-gray-500" />
                      Waive Deadline
                    </button>
                  </div>
                )}
              </div>
            )}
            {deadline.status === 'completed' && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Completed
              </span>
            )}
            {deadline.status === 'waived' && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Waived
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Waive Modal */}
      {showWaiveModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowWaiveModal(false)} />
            <div className="relative w-full max-w-md rounded-lg bg-white shadow-xl p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Waive Deadline
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Please provide a reason for waiving this deadline.
              </p>
              <textarea
                value={waiveReason}
                onChange={(e) => setWaiveReason(e.target.value)}
                placeholder="Reason for waiving..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                rows={3}
              />
              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => setShowWaiveModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-500"
                >
                  Cancel
                </button>
                <button
                  onClick={handleWaive}
                  disabled={!waiveReason.trim() || isActioning}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-gray-600 hover:bg-gray-700 disabled:opacity-50"
                >
                  {isActioning && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Waive Deadline
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Extend Modal */}
      {showExtendModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowExtendModal(false)} />
            <div className="relative w-full max-w-md rounded-lg bg-white shadow-xl p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Extend Deadline
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    New Due Date
                  </label>
                  <input
                    type="date"
                    value={extendDate}
                    onChange={(e) => setExtendDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Reason for Extension
                  </label>
                  <textarea
                    value={extendReason}
                    onChange={(e) => setExtendReason(e.target.value)}
                    placeholder="Reason for extending..."
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                    rows={3}
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => setShowExtendModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-500"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExtend}
                  disabled={!extendDate || !extendReason.trim() || isActioning}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
                >
                  {isActioning && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Extend Deadline
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function DeadlinesPage() {
  const searchParams = useSearchParams();
  const transactionId = searchParams.get('transaction');
  const [statusFilter, setStatusFilter] = useState('');
  const [actioningId, setActioningId] = useState<string | null>(null);

  const { data: deadlines, isLoading } = useDeadlines(
    transactionId || undefined,
    { status: statusFilter || undefined }
  );
  const completeDeadline = useCompleteDeadline();
  const waiveDeadline = useWaiveDeadline();
  const extendDeadline = useExtendDeadline();

  const handleComplete = async (id: string) => {
    setActioningId(id);
    try {
      await completeDeadline.mutateAsync(id);
    } finally {
      setActioningId(null);
    }
  };

  const handleWaive = async (id: string, reason: string) => {
    setActioningId(id);
    try {
      await waiveDeadline.mutateAsync({ id, reason });
    } finally {
      setActioningId(null);
    }
  };

  const handleExtend = async (id: string, newDate: string, reason: string) => {
    setActioningId(id);
    try {
      await extendDeadline.mutateAsync({ id, newDate, reason });
    } finally {
      setActioningId(null);
    }
  };

  // Group deadlines by status
  const overdueDeadlines = deadlines?.filter(
    (d) => new Date(d.due_date) < new Date() && d.status === 'pending'
  );
  const upcomingDeadlines = deadlines?.filter(
    (d) => new Date(d.due_date) >= new Date() && d.status === 'pending'
  );
  const completedDeadlines = deadlines?.filter(
    (d) => d.status === 'completed' || d.status === 'waived'
  );

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Deadlines</h1>
            <p className="mt-1 text-sm text-gray-500">
              Track and manage transaction deadlines
            </p>
          </div>
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-gray-400 mr-2" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : deadlines && deadlines.length > 0 ? (
          <div className="space-y-6">
            {/* Overdue Section */}
            {overdueDeadlines && overdueDeadlines.length > 0 && (
              <div>
                <h2 className="text-lg font-medium text-red-600 mb-3 flex items-center">
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Overdue ({overdueDeadlines.length})
                </h2>
                <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
                  {overdueDeadlines.map((deadline) => (
                    <DeadlineRow
                      key={deadline.id}
                      deadline={deadline}
                      onComplete={() => handleComplete(deadline.id)}
                      onWaive={(reason) => handleWaive(deadline.id, reason)}
                      onExtend={(newDate, reason) =>
                        handleExtend(deadline.id, newDate, reason)
                      }
                      isActioning={actioningId === deadline.id}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Upcoming Section */}
            {upcomingDeadlines && upcomingDeadlines.length > 0 && (
              <div>
                <h2 className="text-lg font-medium text-gray-900 mb-3 flex items-center">
                  <Clock className="h-5 w-5 mr-2 text-blue-500" />
                  Upcoming ({upcomingDeadlines.length})
                </h2>
                <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
                  {upcomingDeadlines.map((deadline) => (
                    <DeadlineRow
                      key={deadline.id}
                      deadline={deadline}
                      onComplete={() => handleComplete(deadline.id)}
                      onWaive={(reason) => handleWaive(deadline.id, reason)}
                      onExtend={(newDate, reason) =>
                        handleExtend(deadline.id, newDate, reason)
                      }
                      isActioning={actioningId === deadline.id}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Completed Section */}
            {completedDeadlines && completedDeadlines.length > 0 && (
              <div>
                <h2 className="text-lg font-medium text-gray-500 mb-3 flex items-center">
                  <CheckCircle className="h-5 w-5 mr-2 text-green-500" />
                  Completed ({completedDeadlines.length})
                </h2>
                <div className="bg-white shadow rounded-lg divide-y divide-gray-200 opacity-75">
                  {completedDeadlines.map((deadline) => (
                    <DeadlineRow
                      key={deadline.id}
                      deadline={deadline}
                      onComplete={() => {}}
                      onWaive={() => {}}
                      onExtend={() => {}}
                      isActioning={false}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <Calendar className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No deadlines</h3>
            <p className="mt-2 text-sm text-gray-500">
              Deadlines will appear here when you create transactions.
            </p>
            <Link
              href="/transactions"
              className="mt-4 inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              View transactions
            </Link>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
