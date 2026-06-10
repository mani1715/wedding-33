import React from 'react';
import { FileText, CheckCircle, Globe, Archive } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const statusConfig = {
    draft: {
      label: 'Draft',
      icon: FileText,
      className: 'bg-gray-100 text-gray-700 border-gray-300',
      iconColor: 'text-gray-500'
    },
    ready: {
      label: 'Ready',
      icon: CheckCircle,
      className: 'bg-blue-100 text-blue-700 border-blue-300',
      iconColor: 'text-blue-500'
    },
    published: {
      label: 'Published',
      icon: Globe,
      className: 'bg-green-100 text-green-700 border-green-300',
      iconColor: 'text-green-500'
    },
    archived: {
      label: 'Archived',
      icon: Archive,
      className: 'bg-orange-100 text-orange-700 border-orange-300',
      iconColor: 'text-orange-500'
    }
  };

  const config = statusConfig[status] || statusConfig.draft;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${config.className}`}>
      <Icon className={`w-3.5 h-3.5 ${config.iconColor}`} />
      {config.label}
    </span>
  );
};

export default StatusBadge;
