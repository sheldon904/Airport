'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useDocumentsNeedingReview, useVerifyDocument, useDocumentExtraction } from '@/hooks';
import {
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronRight,
  Loader2,
  Eye,
  Edit3,
} from 'lucide-react';
import Link from 'next/link';
import { formatDate, formatAddress } from '@/lib/utils';

function ReviewCard({
  document,
  onVerify,
  isVerifying,
}: {
  document: any;
  onVerify: (verified: boolean, corrections?: Record<string, any>) => void;
  isVerifying: boolean;
}) {
  const [showDetails, setShowDetails] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, any>>({});

  const { data: extraction } = useDocumentExtraction(document.id);

  const handleApprove = () => {
    if (isEditing && Object.keys(corrections).length > 0) {
      onVerify(true, corrections);
    } else {
      onVerify(true);
    }
  };

  const handleReject = () => {
    onVerify(false);
  };

  const confidencePercent = document.confidence_score
    ? Math.round(document.confidence_score * 100)
    : 0;

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              <div className="h-12 w-12 rounded-lg bg-yellow-100 flex items-center justify-center">
                <FileText className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">
                {document.filename}
              </h3>
              <p className="text-sm text-gray-500 capitalize">
                {document.document_type.replace('_', ' ')}
              </p>
              {document.transaction && (
                <Link
                  href={`/transactions/${document.transaction.id}`}
                  className="text-sm text-primary-600 hover:text-primary-500"
                >
                  {formatAddress(document.transaction.property_address)}
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                confidencePercent >= 85
                  ? 'bg-green-100 text-green-800'
                  : confidencePercent >= 70
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {confidencePercent}% confidence
            </span>
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">AI Confidence</span>
            <span className="font-medium">{confidencePercent}%</span>
          </div>
          <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                confidencePercent >= 85
                  ? 'bg-green-500'
                  : confidencePercent >= 70
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
        </div>

        {/* Extracted Data Preview */}
        {extraction && (
          <div className="mt-4">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="flex items-center text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              <Eye className="h-4 w-4 mr-1" />
              {showDetails ? 'Hide' : 'View'} Extracted Data
              <ChevronRight
                className={`h-4 w-4 ml-1 transition-transform ${
                  showDetails ? 'rotate-90' : ''
                }`}
              />
            </button>

            {showDetails && (
              <div className="mt-3 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-900">
                    Extracted Fields
                  </h4>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="inline-flex items-center text-xs font-medium text-primary-600 hover:text-primary-500"
                  >
                    <Edit3 className="h-3 w-3 mr-1" />
                    {isEditing ? 'Cancel Edit' : 'Edit Values'}
                  </button>
                </div>
                <dl className="space-y-2">
                  {Object.entries(extraction.extracted_data || {}).map(
                    ([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between py-1 border-b border-gray-200 last:border-0"
                      >
                        <dt className="text-sm text-gray-500 capitalize">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        {isEditing ? (
                          <input
                            type="text"
                            defaultValue={String(value)}
                            onChange={(e) =>
                              setCorrections({
                                ...corrections,
                                [key]: e.target.value,
                              })
                            }
                            className="text-sm border-gray-300 rounded px-2 py-1"
                          />
                        ) : (
                          <dd className="text-sm font-medium text-gray-900">
                            {String(value)}
                          </dd>
                        )}
                      </div>
                    )
                  )}
                </dl>
                {extraction.flags && extraction.flags.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <h5 className="text-sm font-medium text-yellow-800 mb-2">
                      AI Flags
                    </h5>
                    <ul className="space-y-1">
                      {extraction.flags.map((flag: string, i: number) => (
                        <li
                          key={i}
                          className="flex items-start text-sm text-yellow-700"
                        >
                          <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0 mt-0.5" />
                          {flag}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end space-x-3">
          <button
            onClick={handleReject}
            disabled={isVerifying}
            className="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
          >
            <XCircle className="h-4 w-4 mr-2" />
            Reject & Reprocess
          </button>
          <button
            onClick={handleApprove}
            disabled={isVerifying}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
          >
            {isVerifying ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4 mr-2" />
            )}
            {isEditing && Object.keys(corrections).length > 0
              ? 'Approve with Corrections'
              : 'Approve'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DocumentReviewPage() {
  const { data: documents, isLoading } = useDocumentsNeedingReview();
  const verifyDocument = useVerifyDocument();
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  const handleVerify = async (
    docId: string,
    verified: boolean,
    corrections?: Record<string, any>
  ) => {
    setVerifyingId(docId);
    try {
      await verifyDocument.mutateAsync({ id: docId, verified, corrections });
    } finally {
      setVerifyingId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Review Queue</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review and verify AI-extracted document data. Documents below the
            confidence threshold require human verification.
          </p>
        </div>

        {/* Info Banner */}
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-blue-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Human-in-the-Loop Verification
              </h3>
              <p className="mt-1 text-sm text-blue-700">
                Documents with AI confidence below 85% are flagged for review.
                Verify the extracted data is correct, make corrections if needed,
                then approve or reject for reprocessing.
              </p>
            </div>
          </div>
        </div>

        {/* Review Queue */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : documents && documents.length > 0 ? (
          <div className="space-y-4">
            {documents.map((doc) => (
              <ReviewCard
                key={doc.id}
                document={doc}
                onVerify={(verified, corrections) =>
                  handleVerify(doc.id, verified, corrections)
                }
                isVerifying={verifyingId === doc.id}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              All caught up!
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              No documents require review at this time.
            </p>
            <Link
              href="/dashboard"
              className="mt-4 inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              Back to dashboard
            </Link>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
