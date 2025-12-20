'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useDashboard, useTransactions } from '@/hooks';
import { useUpcomingDeadlines, useDocumentsNeedingReview } from '@/hooks';
import {
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Calendar,
  DollarSign,
  AlertCircle,
} from 'lucide-react';
import Link from 'next/link';
import { formatCurrency, formatDate, getStatusColor, formatAddress } from '@/lib/utils';

function StatCard({
  title,
  value,
  icon: Icon,
  change,
  href,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  change?: string;
  href?: string;
}) {
  const content = (
    <div className="rounded-lg bg-white p-6 shadow">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className="h-8 w-8 text-primary-600" />
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {change && (
            <p className="text-sm text-green-600 flex items-center mt-1">
              <TrendingUp className="h-4 w-4 mr-1" />
              {change}
            </p>
          )}
        </div>
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block hover:opacity-90 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

function DeadlineItem({
  title,
  dueDate,
  transaction,
  isOverdue,
}: {
  title: string;
  dueDate: string;
  transaction: string;
  isOverdue: boolean;
}) {
  return (
    <div className="flex items-center py-3">
      <div
        className={`flex-shrink-0 w-2 h-2 rounded-full ${
          isOverdue ? 'bg-red-500' : 'bg-yellow-500'
        }`}
      />
      <div className="ml-4 flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{title}</p>
        <p className="text-sm text-gray-500 truncate">{transaction}</p>
      </div>
      <div className="ml-4 flex-shrink-0">
        <p
          className={`text-sm font-medium ${
            isOverdue ? 'text-red-600' : 'text-gray-600'
          }`}
        >
          {formatDate(dueDate)}
        </p>
      </div>
    </div>
  );
}

function TransactionRow({
  id,
  address,
  status,
  price,
  closingDate,
}: {
  id: string;
  address: string;
  status: string;
  price?: number;
  closingDate?: string;
}) {
  const statusColors = getStatusColor(status);

  return (
    <Link
      href={`/transactions/${id}`}
      className="block hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center py-4 px-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{address}</p>
          {closingDate && (
            <p className="text-sm text-gray-500">
              Closing: {formatDate(closingDate)}
            </p>
          )}
        </div>
        <div className="ml-4 flex items-center space-x-4">
          {price && (
            <span className="text-sm font-medium text-gray-900">
              {formatCurrency(price)}
            </span>
          )}
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors}`}
          >
            {status.replace('_', ' ')}
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: dashboard, isLoading: dashboardLoading } = useDashboard();
  const { data: transactions, isLoading: transactionsLoading } = useTransactions({
    limit: 5,
  });
  const { data: upcomingDeadlines, isLoading: deadlinesLoading } =
    useUpcomingDeadlines(7);
  const { data: reviewQueue, isLoading: reviewLoading } =
    useDocumentsNeedingReview();

  const isLoading =
    dashboardLoading || transactionsLoading || deadlinesLoading || reviewLoading;

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg" />
            ))}
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="h-80 bg-gray-200 rounded-lg" />
            <div className="h-80 bg-gray-200 rounded-lg" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const stats = dashboard || {
    active_transactions: 0,
    pending_deadlines: 0,
    documents_needing_review: 0,
    completed_this_month: 0,
    total_volume: 0,
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Overview of your transaction coordination activity
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Active Transactions"
            value={stats.active_transactions}
            icon={FileText}
            href="/transactions"
          />
          <StatCard
            title="Pending Deadlines"
            value={stats.pending_deadlines}
            icon={Clock}
            href="/deadlines"
          />
          <StatCard
            title="Documents to Review"
            value={stats.documents_needing_review}
            icon={AlertCircle}
            href="/documents/review"
          />
          <StatCard
            title="Completed This Month"
            value={stats.completed_this_month}
            icon={CheckCircle}
          />
        </div>

        {/* Total Volume Banner */}
        {stats.total_volume > 0 && (
          <div className="rounded-lg bg-gradient-to-r from-primary-600 to-primary-700 p-6 shadow">
            <div className="flex items-center">
              <DollarSign className="h-10 w-10 text-white" />
              <div className="ml-4">
                <p className="text-sm font-medium text-primary-100">
                  Total Active Volume
                </p>
                <p className="text-3xl font-bold text-white">
                  {formatCurrency(stats.total_volume)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Recent Transactions */}
          <div className="rounded-lg bg-white shadow">
            <div className="border-b border-gray-200 px-4 py-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">
                Recent Transactions
              </h2>
              <Link
                href="/transactions"
                className="text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                View all
              </Link>
            </div>
            <div className="divide-y divide-gray-200">
              {transactions && transactions.length > 0 ? (
                transactions.map((tx) => (
                  <TransactionRow
                    key={tx.id}
                    id={tx.id}
                    address={formatAddress(tx.property_address)}
                    status={tx.status}
                    price={tx.purchase_price}
                    closingDate={tx.closing_date}
                  />
                ))
              ) : (
                <div className="py-8 text-center">
                  <FileText className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-500">
                    No transactions yet
                  </p>
                  <Link
                    href="/transactions?new=true"
                    className="mt-4 inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-500"
                  >
                    Create your first transaction
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Upcoming Deadlines */}
          <div className="rounded-lg bg-white shadow">
            <div className="border-b border-gray-200 px-4 py-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">
                Upcoming Deadlines
              </h2>
              <Link
                href="/deadlines"
                className="text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                View all
              </Link>
            </div>
            <div className="px-4 divide-y divide-gray-200">
              {upcomingDeadlines && upcomingDeadlines.length > 0 ? (
                upcomingDeadlines.slice(0, 5).map((deadline) => (
                  <DeadlineItem
                    key={deadline.id}
                    title={deadline.title}
                    dueDate={deadline.due_date}
                    transaction={formatAddress(
                      deadline.transaction?.property_address || {}
                    )}
                    isOverdue={new Date(deadline.due_date) < new Date()}
                  />
                ))
              ) : (
                <div className="py-8 text-center">
                  <Calendar className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-500">
                    No upcoming deadlines
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Review Queue Alert */}
        {reviewQueue && reviewQueue.length > 0 && (
          <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4">
            <div className="flex">
              <AlertTriangle className="h-5 w-5 text-yellow-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  Documents Requiring Review
                </h3>
                <p className="mt-1 text-sm text-yellow-700">
                  You have {reviewQueue.length} document(s) that need human
                  verification before proceeding.
                </p>
                <Link
                  href="/documents/review"
                  className="mt-2 inline-flex items-center text-sm font-medium text-yellow-800 hover:text-yellow-900"
                >
                  Review now &rarr;
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
