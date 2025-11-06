export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

export const MODE_INFO = {
  recruiter: {
    label: 'Recruiter',
    icon: '💼',
    description: 'Business-focused summaries'
  },
  engineer: {
    label: 'Engineer',
    icon: '⚙️',
    description: 'Technical deep dives'
  },
  ama: {
    label: 'AMA',
    icon: '💬',
    description: 'Conversational Q&A'
  }
};
