import React, { useState, useEffect } from 'react';
import { 
  Mail, CheckCircle, XCircle, Edit3, Send, 
  RefreshCw, TrendingUp, Inbox, Clock, AlertCircle,
  Sparkles, Zap, User, Calendar, ChevronRight, Bell
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [pendingEmails, setPendingEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [selectedEmails, setSelectedEmails] = useState(new Set());
  const [editingEmail, setEditingEmail] = useState(null);
  const [editedResponse, setEditedResponse] = useState('');
  const [notification, setNotification] = useState(null);
  const [expandedEmailBody, setExpandedEmailBody] = useState(false);  // NEW

  useEffect(() => {
    fetchPending();
    fetchStats();
    const interval = setInterval(() => {
      fetchStats();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Auto-select first email if none selected
    if (pendingEmails.length > 0 && !selectedEmail) {
      setSelectedEmail(pendingEmails[0]);
    }
  }, [pendingEmails]);

  useEffect(() => {
    // Show browser notification for pending emails
    if (stats && stats.pending_approvals > 0) {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Email Automation', {
          body: `${stats.pending_approvals} email${stats.pending_approvals > 1 ? 's' : ''} pending approval`,
          icon: '📧',
          tag: 'email-pending'
        });
      }
    }
  }, [stats?.pending_approvals]);

  // Request notification permission on load
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const fetchPending = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pending`);
      const data = await response.json();
      setPendingEmails(data);
    } catch (error) {
      console.error('Error fetching pending:', error);
      showNotification('Failed to fetch pending emails', 'error');
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const processEmails = async () => {
    setProcessing(true);
    try {
      const response = await fetch(`${API_BASE}/api/emails/process`, {
        method: 'POST'
      });
      const data = await response.json();
      showNotification(`🎉 Processed ${data.processed_count} emails successfully!`);
      await fetchPending();
      await fetchStats();
    } catch (error) {
      console.error('Error processing emails:', error);
      showNotification('Failed to process emails', 'error');
    } finally {
      setProcessing(false);
    }
  };

  const handleApprove = async (emailId, action, editedText = null) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/approve/${emailId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_id: emailId,
          action: action,
          edited_response: editedText
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const actionEmoji = action === 'approve' ? '✅' : action === 'reject' ? '❌' : action === 'save_edit' ? '💾' : '📝';
        const actionText = action === 'save_edit' ? 'saved' : action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'sent';
        showNotification(`${actionEmoji} Email ${actionText} successfully!`);
        
        // Refresh pending list to get updated edited_response
        await fetchPending();
        await fetchStats();
        
        // Only remove from list and move to next if not saving
        if (action !== 'save_edit') {
          const currentIndex = pendingEmails.findIndex(e => e.email_id === emailId);
          const nextEmail = pendingEmails[currentIndex + 1] || pendingEmails[currentIndex - 1];
          setSelectedEmail(nextEmail);
          selectedEmails.delete(emailId);
          setSelectedEmails(new Set(selectedEmails));
          setEditingEmail(null);
        } else {
          // If saving, keep the email selected and exit edit mode
          setEditingEmail(null);
          // Update the selected email with the new edited response
          const updatedEmail = pendingEmails.find(e => e.email_id === emailId);
          if (updatedEmail) {
            setSelectedEmail(updatedEmail);
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      showNotification('Action failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchApprove = async () => {
    if (selectedEmails.size === 0) return;
    
    setLoading(true);
    const approvals = Array.from(selectedEmails).map(id => ({
      email_id: id,
      action: 'approve'
    }));

    console.log('Sending batch request:', { approvals });

    try {
      const response = await fetch(`${API_BASE}/api/batch-approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approvals })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        showNotification(`Batch approval failed: ${response.status}`, 'error');
        setLoading(false);
        return;
      }
      
      const data = await response.json();
      console.log('Success response:', data);
      showNotification(`🚀 Approved ${data.successful} of ${data.total} emails!`);
      await fetchPending();
      await fetchStats();
      setSelectedEmails(new Set());
      setSelectedEmail(null);
    } catch (error) {
      console.error('Error:', error);
      showNotification('Batch approval failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchReject = async () => {
    if (selectedEmails.size === 0) return;
    
    setLoading(true);
    const approvals = Array.from(selectedEmails).map(id => ({
      email_id: id,
      action: 'reject'
    }));

    console.log('Sending batch reject:', { approvals });

    try {
      const response = await fetch(`${API_BASE}/api/batch-approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approvals })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        showNotification(`Batch reject failed: ${response.status}`, 'error');
        setLoading(false);
        return;
      }
      
      const data = await response.json();
      console.log('Success response:', data);
      showNotification(`🗑️ Rejected ${data.successful} of ${data.total} emails`);
      await fetchPending();
      await fetchStats();
      setSelectedEmails(new Set());
      setSelectedEmail(null);
    } catch (error) {
      console.error('Error:', error);
      showNotification('Batch reject failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelection = (emailId) => {
    const newSelected = new Set(selectedEmails);
    if (newSelected.has(emailId)) {
      newSelected.delete(emailId);
    } else {
      newSelected.add(emailId);
    }
    setSelectedEmails(newSelected);
  };

  const selectAll = () => {
    if (selectedEmails.size === pendingEmails.length) {
      setSelectedEmails(new Set());
    } else {
      setSelectedEmails(new Set(pendingEmails.map(e => e.email_id)));
    }
  };

  const getPriorityColor = (priority) => {
    if (priority >= 4) return 'from-red-500 to-pink-500';
    if (priority === 3) return 'from-yellow-500 to-orange-500';
    return 'from-green-500 to-emerald-500';
  };

  const getPriorityBadge = (priority) => {
    if (priority >= 4) return 'bg-red-100 text-red-700 border-red-200';
    if (priority === 3) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    return 'bg-green-100 text-green-700 border-green-200';
  };

  const getCategoryStyle = (category) => {
    const styles = {
      urgent: 'bg-gradient-to-r from-red-500 to-pink-500 text-white',
      work: 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white',
      personal: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
      support: 'bg-gradient-to-r from-green-500 to-emerald-500 text-white',
      marketing: 'bg-gradient-to-r from-gray-500 to-slate-500 text-white'
    };
    return styles[category] || 'bg-gradient-to-r from-gray-500 to-slate-500 text-white';
  };

  const getSentimentEmoji = (sentiment) => {
    if (sentiment === 'positive') return '😊';
    if (sentiment === 'negative') return '😟';
    return '😐';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-10 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-6 right-6 z-50 px-6 py-4 rounded-2xl shadow-2xl backdrop-blur-sm transform transition-all duration-300 ${
          notification.type === 'success' 
            ? 'bg-gradient-to-r from-green-500 to-emerald-500' 
            : 'bg-gradient-to-r from-red-500 to-pink-500'
        } text-white animate-slide-in-right flex items-center space-x-3`}>
          {notification.type === 'success' ? (
            <CheckCircle className="w-6 h-6" />
          ) : (
            <AlertCircle className="w-6 h-6" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur opacity-75 animate-pulse"></div>
                <div className="relative bg-gradient-to-r from-blue-500 to-purple-600 p-3 rounded-2xl">
                  <Mail className="w-7 h-7 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Email Automation
                </h1>
                <p className="text-sm text-gray-600 flex items-center space-x-1">
                  <Sparkles className="w-4 h-4" />
                  <span>AI-Powered Response Management</span>
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Pending Count Badge */}
              {stats && stats.pending_approvals > 0 && (
                <div className="flex items-center space-x-2 bg-red-100 text-red-700 px-4 py-2 rounded-xl border-2 border-red-200 animate-pulse">
                  <Bell className="w-5 h-5" />
                  <span className="font-bold">{stats.pending_approvals} Pending</span>
                </div>
              )}
              
              <button
                onClick={processEmails}
                disabled={processing}
                className="group relative px-6 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 hover:from-blue-600 hover:via-purple-600 hover:to-pink-600 transition-all duration-300 disabled:opacity-50 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none"
              >
                <div className="flex items-center space-x-2">
                  <RefreshCw className={`w-5 h-5 ${processing ? 'animate-spin' : ''}`} />
                  <span>{processing ? 'Processing...' : 'Process New'}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Split View */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Sidebar - Email Queue (30%) */}
        <div className="w-[30%] bg-white/50 backdrop-blur-sm border-r border-gray-200/50 overflow-hidden flex flex-col">
          {/* Stats Summary */}
          {stats && (
            <div className="p-4 border-b border-gray-200/50 bg-white/80">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-3 border border-blue-200">
                  <p className="text-xs text-blue-600 font-medium">Pending</p>
                  <p className="text-2xl font-bold text-blue-700">{stats.pending_approvals}</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-3 border border-green-200">
                  <p className="text-xs text-green-600 font-medium">Today</p>
                  <p className="text-2xl font-bold text-green-700">{stats.processed_today}</p>
                </div>
              </div>
            </div>
          )}

          {/* Batch Actions */}
          {selectedEmails.size > 0 && (
            <div className="p-3 border-b border-gray-200/50 bg-gradient-to-r from-blue-500 to-purple-500">
              <div className="bg-white rounded-lg p-3">
                <p className="text-sm font-semibold text-gray-900 mb-2">{selectedEmails.size} selected</p>
                <div className="flex space-x-2">
                  <button
                    onClick={handleBatchApprove}
                    disabled={loading}
                    className="flex-1 flex items-center justify-center space-x-1 bg-green-500 text-white px-3 py-2 rounded-lg hover:bg-green-600 text-sm font-medium"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Approve</span>
                  </button>
                  <button
                    onClick={handleBatchReject}
                    disabled={loading}
                    className="flex-1 flex items-center justify-center space-x-1 bg-red-500 text-white px-3 py-2 rounded-lg hover:bg-red-600 text-sm font-medium"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Email Queue List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {pendingEmails.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <Inbox className="w-16 h-16 text-gray-400 mb-3" />
                <p className="text-gray-600 font-medium">No pending emails</p>
                <p className="text-sm text-gray-500">All caught up!</p>
              </div>
            ) : (
              pendingEmails.map((email) => (
                <div
                  key={email.email_id}
                  onClick={() => setSelectedEmail(email)}
                  className={`group cursor-pointer rounded-xl p-3 transition-all duration-200 ${
                    selectedEmail?.email_id === email.email_id
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg scale-105'
                      : 'bg-white/80 hover:bg-white hover:shadow-md'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      checked={selectedEmails.has(email.email_id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleSelection(email.email_id);
                      }}
                      className="mt-1 w-4 h-4 rounded cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                          selectedEmail?.email_id === email.email_id
                            ? 'bg-white/20 text-white'
                            : getCategoryStyle(email.category)
                        }`}>
                          {email.category}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                          selectedEmail?.email_id === email.email_id
                            ? 'bg-white/20 text-white'
                            : getPriorityBadge(email.priority)
                        }`}>
                          P{email.priority}
                        </span>
                      </div>
                      <h3 className={`font-semibold text-sm truncate ${
                        selectedEmail?.email_id === email.email_id ? 'text-white' : 'text-gray-900'
                      }`}>
                        {email.subject}
                      </h3>
                      <p className={`text-xs truncate ${
                        selectedEmail?.email_id === email.email_id ? 'text-white/80' : 'text-gray-600'
                      }`}>
                        {email.sender}
                      </p>
                    </div>
                    <ChevronRight className={`w-5 h-5 ${
                      selectedEmail?.email_id === email.email_id ? 'text-white' : 'text-gray-400'
                    }`} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side - Email Details (70%) */}
        <div className="flex-1 overflow-y-auto p-6">
          {!selectedEmail ? (
            <div className="flex flex-col items-center justify-center h-full">
              <Mail className="w-24 h-24 text-gray-300 mb-4" />
              <h3 className="text-2xl font-bold text-gray-700 mb-2">Select an email</h3>
              <p className="text-gray-500">Choose an email from the queue to review</p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              {/* Email Header */}
              <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl p-6 mb-6 border-2 border-gray-200/50">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h1 className="text-3xl font-bold text-gray-900 mb-3">{selectedEmail.subject}</h1>
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${getCategoryStyle(selectedEmail.category)} shadow-md`}>
                        {selectedEmail.category}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-bold border-2 ${getPriorityBadge(selectedEmail.priority)}`}>
                        Priority {selectedEmail.priority}
                      </span>
                      <span className="px-3 py-1 rounded-full text-sm font-semibold bg-gray-100 text-gray-700">
                        {getSentimentEmoji(selectedEmail.sentiment)} {selectedEmail.sentiment}
                      </span>
                      <span className="px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-700">
                        {(selectedEmail.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <User className="w-4 h-4" />
                      <span className="font-medium">{selectedEmail.sender}</span>
                    </div>
                  </div>
                </div>

                {/* Email Body */}
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200">
                  <p className="text-sm font-bold text-gray-700 mb-3 flex items-center space-x-2">
                    <Mail className="w-4 h-4" />
                    <span>Email Content</span>
                  </p>
                  <div className={`text-sm text-gray-800 leading-relaxed ${expandedEmailBody ? '' : 'max-h-64'} overflow-y-auto`}>
                    <p className="whitespace-pre-wrap break-words">
                      {expandedEmailBody ? selectedEmail.body_full : selectedEmail.body_preview}
                    </p>
                  </div>
                  {selectedEmail.body_full && selectedEmail.body_full.length > 300 && (
                    <button
                      onClick={() => setExpandedEmailBody(!expandedEmailBody)}
                      className="mt-3 text-blue-600 hover:text-blue-700 font-semibold text-sm flex items-center space-x-1"
                    >
                      <span>{expandedEmailBody ? 'See Less' : 'See More'}</span>
                      <ChevronRight className={`w-4 h-4 transform transition-transform ${expandedEmailBody ? 'rotate-90' : ''}`} />
                    </button>
                  )}
                </div>
              </div>

              {/* AI Response */}
              <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl p-6 mb-6 border-2 border-blue-200">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-5 h-5 text-blue-600" />
                    <h2 className="text-xl font-bold text-gray-900">AI Generated Response</h2>
                  </div>
                  <span className="text-sm font-bold text-blue-700 bg-blue-100 px-4 py-2 rounded-full border-2 border-blue-300">
                    {selectedEmail.tone}
                  </span>
                </div>

                {editingEmail === selectedEmail.email_id ? (
                  <textarea
                    value={editedResponse}
                    onChange={(e) => setEditedResponse(e.target.value)}
                    className="w-full p-4 border-2 border-blue-300 rounded-xl focus:ring-4 focus:ring-blue-200 focus:border-blue-500 transition-all font-sans text-sm"
                    rows="12"
                  />
                ) : (
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 text-sm text-gray-800 leading-relaxed max-h-80 overflow-y-auto border border-blue-200">
                    <p className="whitespace-pre-wrap break-words">
                      {selectedEmail.edited_response || selectedEmail.draft_response}
                    </p>
                    {selectedEmail.edited_response && (
                      <div className="mt-3 items-center space-x-2 text-xs text-blue-700 bg-blue-100 px-3 py-1 rounded-full inline-flex">
                        <Edit3 className="w-3 h-3" />
                        <span>Custom response saved</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-gray-200/50">
                <div className="flex items-center justify-between">
                  {editingEmail === selectedEmail.email_id ? (
                    <>
                      <button
                        onClick={() => setEditingEmail(null)}
                        className="px-6 py-3 text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors font-semibold"
                      >
                        Cancel
                      </button>
                      <div className="flex space-x-3">
                        <button
                          onClick={() => handleApprove(selectedEmail.email_id, 'save_edit', editedResponse)}
                          disabled={loading}
                          className="flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-xl hover:from-purple-600 hover:to-pink-600 transition-all disabled:opacity-50 font-semibold shadow-lg"
                        >
                          <Edit3 className="w-5 h-5" />
                          <span>Save (Don't Send)</span>
                        </button>
                        <button
                          onClick={() => handleApprove(selectedEmail.email_id, 'edit', editedResponse)}
                          disabled={loading}
                          className="flex items-center space-x-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-8 py-3 rounded-xl hover:from-blue-600 hover:to-indigo-600 transition-all disabled:opacity-50 font-semibold shadow-lg text-lg"
                        >
                          <Send className="w-6 h-6" />
                          <span>Save & Send Now</span>
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex space-x-3">
                        <button
                          onClick={() => handleApprove(selectedEmail.email_id, 'reject')}
                          disabled={loading}
                          className="flex items-center space-x-2 text-red-600 bg-red-50 px-6 py-3 rounded-xl hover:bg-red-100 transition-all disabled:opacity-50 font-semibold border-2 border-red-200"
                        >
                          <XCircle className="w-5 h-5" />
                          <span>Reject</span>
                        </button>
                        <button
                          onClick={() => {
                            setEditingEmail(selectedEmail.email_id);
                            setEditedResponse(selectedEmail.draft_response);
                          }}
                          className="flex items-center space-x-2 text-blue-600 bg-blue-50 px-6 py-3 rounded-xl hover:bg-blue-100 transition-all font-semibold border-2 border-blue-200"
                        >
                          <Edit3 className="w-5 h-5" />
                          <span>Edit Response</span>
                        </button>
                      </div>
                      <button
                        onClick={() => handleApprove(selectedEmail.email_id, 'approve')}
                        disabled={loading}
                        className="flex items-center space-x-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-8 py-3 rounded-xl hover:from-green-600 hover:to-emerald-600 transition-all disabled:opacity-50 font-semibold shadow-lg text-lg"
                      >
                        <CheckCircle className="w-6 h-6" />
                        <span>Approve & Send</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;