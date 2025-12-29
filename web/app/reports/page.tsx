'use client';

import { useState } from 'react';
import { useOrganizationReport } from '@/hooks/use-reports';
import { useTransactions } from '@/hooks/use-transactions';
import {
  FileText,
  Download,
  AlertTriangle,
  CheckCircle,
  Clock,
  Building2,
  TrendingUp,
  Calendar,
} from 'lucide-react';
import { RISK_LEVEL_COLORS } from '@/types';
import Link from 'next/link';

export default function ReportsPage() {
  const { data: orgReport, isLoading: orgLoading } = useOrganizationReport();
  const { data: transactions, isLoading: txLoading } = useTransactions({ status: 'active' });

  if (orgLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-gray-600 mt-1">
          Organization overview and compliance reporting
        </p>
      </div>

      {/* Organization Overview Cards */}
      {orgReport && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Active Transactions</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {orgReport.active_transactions}
                  </p>
                </div>
                <Building2 className="h-10 w-10 text-blue-500" />
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {orgReport.pending_close_transactions} pending close
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Compliance Rate</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {orgReport.overall_compliance_rate.toFixed(0)}%
                  </p>
                </div>
                <TrendingUp
                  className={`h-10 w-10 ${
                    orgReport.overall_compliance_rate >= 80
                      ? 'text-green-500'
                      : orgReport.overall_compliance_rate >= 50
                      ? 'text-yellow-500'
                      : 'text-red-500'
                  }`}
                />
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {orgReport.transactions_at_risk} at risk
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Closed This Month</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {orgReport.closed_this_month}
                  </p>
                </div>
                <CheckCircle className="h-10 w-10 text-green-500" />
              </div>
              <p className="text-sm text-gray-500 mt-2">
                of {orgReport.total_transactions} total
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Documents to Review</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {orgReport.documents_needing_review}
                  </p>
                </div>
                <FileText
                  className={`h-10 w-10 ${
                    orgReport.documents_needing_review > 0
                      ? 'text-yellow-500'
                      : 'text-gray-400'
                  }`}
                />
              </div>
              <Link
                href="/documents/review"
                className="text-sm text-blue-600 hover:underline mt-2 block"
              >
                View review queue →
              </Link>
            </div>
          </div>

          {/* Alerts Section */}
          {(orgReport.overdue_deadlines.length > 0 ||
            orgReport.transactions_at_risk > 0) && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-8 rounded-r">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
                <h3 className="font-medium text-red-800">Attention Required</h3>
              </div>
              <ul className="mt-2 space-y-1">
                {orgReport.overdue_deadlines.length > 0 && (
                  <li className="text-red-700 text-sm">
                    {orgReport.overdue_deadlines.length} overdue deadline(s)
                  </li>
                )}
                {orgReport.transactions_at_risk > 0 && (
                  <li className="text-red-700 text-sm">
                    {orgReport.transactions_at_risk} transaction(s) at risk
                  </li>
                )}
              </ul>
            </div>
          )}

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upcoming Closings */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-blue-500" />
                  Upcoming Closings
                </h2>
              </div>
              <div className="p-4">
                {orgReport.upcoming_closings.length > 0 ? (
                  <ul className="space-y-3">
                    {orgReport.upcoming_closings.map((closing) => (
                      <li
                        key={closing.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded"
                      >
                        <div>
                          <Link
                            href={`/transactions/${closing.id}`}
                            className="font-medium text-blue-600 hover:underline"
                          >
                            {closing.address}
                          </Link>
                          <p className="text-sm text-gray-500">
                            {closing.closing_date || 'Date TBD'}
                          </p>
                        </div>
                        {closing.days_remaining !== undefined && (
                          <span
                            className={`px-2 py-1 rounded text-sm font-medium ${
                              closing.days_remaining <= 3
                                ? 'bg-red-100 text-red-700'
                                : closing.days_remaining <= 7
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-green-100 text-green-700'
                            }`}
                          >
                            {closing.days_remaining}d
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 text-center py-4">
                    No upcoming closings in the next 14 days
                  </p>
                )}
              </div>
            </div>

            {/* Overdue Deadlines */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Clock className="h-5 w-5 text-red-500" />
                  Overdue Deadlines
                </h2>
              </div>
              <div className="p-4">
                {orgReport.overdue_deadlines.length > 0 ? (
                  <ul className="space-y-3">
                    {orgReport.overdue_deadlines.map((deadline) => (
                      <li
                        key={deadline.id}
                        className="flex items-center justify-between p-3 bg-red-50 rounded"
                      >
                        <div>
                          <p className="font-medium text-red-800">
                            {deadline.name}
                          </p>
                          <p className="text-sm text-red-600">
                            Due: {deadline.due_date}
                          </p>
                        </div>
                        <Link
                          href={`/transactions/${deadline.transaction_id}`}
                          className="text-sm text-blue-600 hover:underline"
                        >
                          View →
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-center py-4">
                    <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                    <p className="text-gray-500">No overdue deadlines</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Transaction Reports Section */}
      <div className="mt-8 bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-500" />
            Generate Transaction Reports
          </h2>
        </div>
        <div className="p-4">
          <p className="text-gray-600 mb-4">
            Select a transaction to generate a detailed compliance report.
          </p>
          {txLoading ? (
            <div className="animate-pulse space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-200 rounded"></div>
              ))}
            </div>
          ) : transactions && transactions.length > 0 ? (
            <ul className="divide-y">
              {transactions.slice(0, 10).map((tx) => (
                <li
                  key={tx.id}
                  className="flex items-center justify-between py-3"
                >
                  <div>
                    <Link
                      href={`/transactions/${tx.id}`}
                      className="font-medium text-gray-900 hover:text-blue-600"
                    >
                      {tx.property_address.street}
                    </Link>
                    <p className="text-sm text-gray-500">
                      {tx.property_address.city}, {tx.property_address.state}
                    </p>
                  </div>
                  <Link
                    href={`/transactions/${tx.id}/report`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
                  >
                    <FileText className="h-4 w-4" />
                    View Report
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No active transactions found
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
