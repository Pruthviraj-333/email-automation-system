import React, { useState, useEffect } from 'react';
import { Mail, Settings, BarChart3, LogOut, CheckCircle, XCircle, Clock, AlertCircle, TrendingUp, Users, Zap } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Mock user state (replace with real auth)
const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = (userData) => {
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('user');
    setUser(null);
  };

  return { user, loading, login, logout };
};

// Landing Page Component
const LandingPage = ({ onGetStarted }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Hero Section */}
      <div className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <div className="flex items-center justify-center mb-6">
            <Zap className="w-16 h-16 text-blue-600" />
          </div>
          <h1 className="text-6xl font-bold text-gray-900 mb-6">
            AI-Powered Email Automation
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Let AI handle your inbox. Review, approve, and send intelligent responses in seconds.
            Save hours every day with smart email automation.
          </p>
          <button
            onClick={onGetStarted}
            className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition shadow-lg"
          >
            Get Started Free →
          </button>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mt-20">
          <div className="bg-white p-8 rounded-xl shadow-md hover:shadow-xl transition">
            <div className="bg-blue-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
              <Mail className="w-7 h-7 text-blue-600" />
            </div>
            <h3 className="text-xl font-bold mb-3">Smart Analysis</h3>
            <p className="text-gray-600">
              AI categorizes emails by urgency, sentiment, and intent automatically
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-md hover:shadow-xl transition">
            <div className="bg-green-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
              <CheckCircle className="w-7 h-7 text-green-600" />
            </div>
            <h3 className="text-xl font-bold mb-3">Human-in-the-Loop</h3>
            <p className="text-gray-600">
              Review AI-generated responses before sending. Full control, zero risk
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-md hover:shadow-xl transition">
            <div className="bg-purple-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
              <TrendingUp className="w-7 h-7 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold mb-3">Save Time</h3>
            <p className="text-gray-600">
              Process 10x more emails in less time with batch approvals
            </p>
          </div>
        </div>

        {/* Stats Section */}
        <div className="mt-20 bg-white rounded-2xl shadow-xl p-12">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-5xl font-bold text-blue-600 mb-2">95%</div>
              <div className="text-gray-600">Time Saved</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-green-600 mb-2">10K+</div>
              <div className="text-gray-600">Emails Processed</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-purple-600 mb-2">4.9★</div>
              <div className="text-gray-600">User Rating</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Auth Component
const AuthPage = ({ onLogin }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '', name: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      if (isSignUp) {
        // Register
        const response = await fetch(`${API_BASE}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: formData.email,
            password: formData.password,
            name: formData.name
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Registration failed');
        }
        
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        onLogin({ 
          email: data.user.email, 
          name: data.user.name,
          gmailConnected: data.user.gmail_connected 
        });
      } else {
        // Login
        const formBody = new URLSearchParams();
        formBody.append('username', formData.email);
        formBody.append('password', formData.password);
        
        const response = await fetch(`${API_BASE}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formBody
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Login failed');
        }
        
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        onLogin({ 
          email: data.user.email, 
          name: data.user.name,
          gmailConnected: data.user.gmail_connected 
        });
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center px-6">
      <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-md w-full">
        <div className="text-center mb-8">
          <Zap className="w-12 h-12 text-blue-600 mx-auto mb-4" />
          <h2 className="text-3xl font-bold text-gray-900">
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-gray-600 mt-2">
            {isSignUp ? 'Start automating your emails' : 'Continue to your dashboard'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          {isSignUp && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required={isSignUp}
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
          >
            {loading ? 'Processing...' : (isSignUp ? 'Sign Up' : 'Login')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            {isSignUp ? 'Already have an account? Login' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
};

// Gmail Connection Component
const GmailConnect = ({ onConnect }) => {
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');

  const handleConnect = async () => {
    setConnecting(true);
    setError('');
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Please login first');
      }
      
      // Get OAuth URL from backend
      const response = await fetch(`${API_BASE}/api/oauth/gmail/connect`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to get OAuth URL');
      }
      
      const data = await response.json();
      
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
      
    } catch (err) {
      setError(err.message);
      setConnecting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center px-6">
      <div className="bg-white rounded-2xl shadow-2xl p-12 max-w-lg w-full text-center">
        <div className="bg-red-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
          <Mail className="w-10 h-10 text-red-600" />
        </div>
        
        <h2 className="text-3xl font-bold text-gray-900 mb-4">Connect Your Gmail</h2>
        <p className="text-gray-600 mb-8">
          We need access to your Gmail to read unread emails and send responses on your behalf.
          Your data is secure and encrypted.
        </p>

        <div className="bg-blue-50 rounded-lg p-6 mb-8 text-left">
          <h3 className="font-semibold text-gray-900 mb-3">We will be able to:</h3>
          <ul className="space-y-2 text-gray-700">
            <li className="flex items-start">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
              <span>Read unread emails from your inbox</span>
            </li>
            <li className="flex items-start">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
              <span>Send email responses on your behalf</span>
            </li>
            <li className="flex items-start">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
              <span>Mark emails as read after processing</span>
            </li>
          </ul>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
            {error}
          </div>
        )}

        <button
          onClick={handleConnect}
          disabled={connecting}
          className="w-full bg-red-600 text-white py-4 rounded-lg font-semibold hover:bg-red-700 transition disabled:opacity-50 flex items-center justify-center"
        >
          {connecting ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Connecting...
            </>
          ) : (
            <>
              <Mail className="w-5 h-5 mr-2" />
              Connect Gmail Account
            </>
          )}
        </button>

        <p className="text-xs text-gray-500 mt-4">
          🔒 Secured by Google OAuth 2.0
        </p>
      </div>
    </div>
  );
};

// Main Dashboard Component
const Dashboard = ({ user, onLogout }) => {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    if (currentPage === 'pending') {
      fetchPending();
    }
  }, [currentPage]);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await fetch(`${API_BASE}/api/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchPending = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await fetch(`${API_BASE}/api/pending`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setPending(data);
    } catch (error) {
      console.error('Error fetching pending:', error);
    }
    setLoading(false);
  };

  const processEmails = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        alert('Please login first');
        return;
      }
      
      await fetch(`${API_BASE}/api/emails/process`, { 
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      await fetchPending();
    } catch (error) {
      console.error('Error processing emails:', error);
      alert('Error processing emails: ' + error.message);
    }
    setLoading(false);
  };

  const handleApproval = async (emailId, action, editedText = null) => {
    try {
      const body = { email_id: emailId, action };
      if (editedText) {
        body.edited_response = editedText;
      }
      
      await fetch(`${API_BASE}/api/approve/${emailId}`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(body)
      });
      setPending(pending.filter(p => p.email_id !== emailId));
      fetchStats();
    } catch (error) {
      console.error('Error approving:', error);
      alert('Failed to process email: ' + error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed left-0 top-0 h-full w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <div className="flex items-center mb-4">
            <Zap className="w-8 h-8 text-blue-600 mr-2" />
            <span className="text-xl font-bold">EmailAI</span>
          </div>
          <div className="text-sm text-gray-600">{user.email}</div>
        </div>

        <nav className="p-4">
          <button
            onClick={() => setCurrentPage('dashboard')}
            className={`w-full flex items-center px-4 py-3 rounded-lg mb-2 transition ${
              currentPage === 'dashboard' ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <BarChart3 className="w-5 h-5 mr-3" />
            Dashboard
          </button>

          <button
            onClick={() => setCurrentPage('pending')}
            className={`w-full flex items-center px-4 py-3 rounded-lg mb-2 transition ${
              currentPage === 'pending' ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Clock className="w-5 h-5 mr-3" />
            Pending Approvals
            {pending.length > 0 && (
              <span className="ml-auto bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                {pending.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setCurrentPage('settings')}
            className={`w-full flex items-center px-4 py-3 rounded-lg mb-2 transition ${
              currentPage === 'settings' ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Settings className="w-5 h-5 mr-3" />
            Settings
          </button>
        </nav>

        <div className="absolute bottom-0 w-full p-4 border-t">
          <button
            onClick={onLogout}
            className="w-full flex items-center px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64 p-8">
        {currentPage === 'dashboard' && (
          <DashboardContent stats={stats} onProcess={processEmails} loading={loading} />
        )}
        {currentPage === 'pending' && (
          <PendingContent pending={pending} onApprove={handleApproval} loading={loading} onProcess={processEmails} />
        )}
        {currentPage === 'settings' && <SettingsContent />}
      </div>
    </div>
  );
};

// Dashboard Content
const DashboardContent = ({ stats, onProcess, loading }) => {
  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <button
          onClick={onProcess}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
        >
          {loading ? 'Processing...' : 'Check New Emails'}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <Mail className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{stats?.total_processed || 0}</div>
          <div className="text-gray-600 text-sm">Total Processed</div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{stats?.by_status?.responded || 0}</div>
          <div className="text-gray-600 text-sm">Responded</div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-yellow-100 p-3 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{stats?.pending_approvals || 0}</div>
          <div className="text-gray-600 text-sm">Pending</div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-purple-100 p-3 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{stats?.processed_today || 0}</div>
          <div className="text-gray-600 text-sm">Today</div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Category Breakdown</h2>
        <div className="space-y-3">
          {stats?.by_category && Object.entries(stats.by_category).map(([category, count]) => (
            <div key={category} className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-blue-500 mr-3"></div>
                <span className="text-gray-700 capitalize">{category}</span>
              </div>
              <span className="font-semibold text-gray-900">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Pending Content
const PendingContent = ({ pending, onApprove, loading, onProcess }) => {
  const [selectedEmail, setSelectedEmail] = useState(null);

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Pending Approvals</h1>
        <button
          onClick={onProcess}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
        >
          {loading ? 'Processing...' : 'Fetch New'}
        </button>
      </div>

      {pending.length === 0 ? (
        <div className="bg-white rounded-xl shadow p-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">All Caught Up!</h3>
          <p className="text-gray-600">No emails pending approval right now.</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {pending.map((email) => (
            <div key={email.email_id} className="bg-white rounded-xl shadow hover:shadow-lg transition p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                      {email.category}
                    </span>
                    <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                      Priority: {email.priority}/5
                    </span>
                    <span className="text-sm text-gray-500">{email.sentiment}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">{email.subject}</h3>
                  <p className="text-gray-600 text-sm">From: {email.sender}</p>
                </div>
              </div>

              <div className="mb-4">
                <p className="text-gray-700 text-sm bg-gray-50 p-4 rounded-lg">
                  {email.body_preview}
                </p>
              </div>

              <div className="mb-4 border-t pt-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-gray-900">Draft Response:</h4>
                  <span className="text-sm text-gray-500">Confidence: {(email.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-gray-800 whitespace-pre-line">{email.draft_response}</p>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => onApprove(email.email_id, 'approve')}
                  className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-green-700 transition flex items-center justify-center"
                >
                  <CheckCircle className="w-5 h-5 mr-2" />
                  Approve & Send
                </button>
                <button
                  onClick={() => setSelectedEmail(email)}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700 transition"
                >
                  Edit Response
                </button>
                <button
                  onClick={() => onApprove(email.email_id, 'reject')}
                  className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-red-700 transition flex items-center justify-center"
                >
                  <XCircle className="w-5 h-5 mr-2" />
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {selectedEmail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full p-6">
            <h3 className="text-xl font-bold mb-4">Edit Response</h3>
            <textarea
              className="w-full h-64 p-4 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500"
              defaultValue={selectedEmail.draft_response}
              id="edit-textarea"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => {
                  const editedText = document.getElementById('edit-textarea').value;
                  onApprove(selectedEmail.email_id, 'edit', editedText);
                  setSelectedEmail(null);
                }}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700"
              >
                Save & Send
              </button>
              <button
                onClick={() => setSelectedEmail(null)}
                className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg font-semibold hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Settings Content
const SettingsContent = () => {
  const [settings, setSettings] = useState({
    autoApprove: false,
    tone: 'friendly',
    autoApproveCategories: []
  });

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>

      <div className="bg-white rounded-xl shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Email Preferences</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Auto-approve Low Priority</h3>
              <p className="text-sm text-gray-600">Automatically send responses for priority 1-2 emails</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.autoApprove}
                onChange={(e) => setSettings({...settings, autoApprove: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Default Response Tone</label>
            <select
              value={settings.tone}
              onChange={(e) => setSettings({...settings, tone: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="formal">Formal</option>
              <option value="friendly">Friendly</option>
              <option value="casual">Casual</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Connected Accounts</h2>
        <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
          <div className="flex items-center">
            <Mail className="w-8 h-8 text-green-600 mr-3" />
            <div>
              <div className="font-medium text-gray-900">Gmail Connected</div>
              <div className="text-sm text-gray-600">Last sync: 5 minutes ago</div>
            </div>
          </div>
          <CheckCircle className="w-6 h-6 text-green-600" />
        </div>
      </div>
    </div>
  );
};

// Main App Component
export default function EmailAutomationApp() {
  const { user, loading, login, logout } = useAuth();
  const [showLanding, setShowLanding] = useState(true);
  const [showAuth, setShowAuth] = useState(false);
  const [showGmailConnect, setShowGmailConnect] = useState(false);

  // Handle OAuth callback
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const state = params.get('state');
      
      if (code && state) {
        try {
          const response = await fetch(`${API_BASE}/api/oauth/gmail/callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, state })
          });
          
          if (response.ok) {
            const data = await response.json();
            // Update user with Gmail connected
            const currentUser = JSON.parse(localStorage.getItem('user'));
            login({ ...currentUser, gmailConnected: true });
            
            // Clear URL params
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        } catch (error) {
          console.error('OAuth callback error:', error);
        }
      }
    };
    
    handleOAuthCallback();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // User not logged in
  if (!user) {
    if (showAuth) {
      return <AuthPage onLogin={(userData) => {
        login(userData);
        setShowAuth(false);
        setShowGmailConnect(true);
      }} />;
    }
    return <LandingPage onGetStarted={() => setShowAuth(true)} />;
  }

  // User logged in but Gmail not connected
  if (!user.gmailConnected) {
    if (showGmailConnect) {
      return <GmailConnect onConnect={() => {
        login({...user, gmailConnected: true});
        setShowGmailConnect(false);
      }} />;
    }
  }

  // User fully set up
  return <Dashboard user={user} onLogout={logout} />;
}