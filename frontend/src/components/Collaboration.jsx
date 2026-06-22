import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Share2, User, Send, ThumbsUp, Reply, MoreVertical, Copy, Check, ExternalLink } from 'lucide-react';

// Comments Component
export function Comments({ comments = [], onAddComment, onDeleteComment, onLikeComment, currentUser }) {
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState(null);
  const [replyText, setReplyText] = useState('');
  const commentsEndRef = useRef(null);

  const scrollToBottom = () => {
    commentsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [comments]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    
    onAddComment?.({
      text: newComment,
      parentId: replyTo,
      timestamp: new Date().toISOString(),
      user: currentUser,
    });
    
    setNewComment('');
    setReplyTo(null);
  };

  const handleReplySubmit = (e) => {
    e.preventDefault();
    if (!replyText.trim() || !replyTo) return;
    
    onAddComment?.({
      text: replyText,
      parentId: replyTo,
      timestamp: new Date().toISOString(),
      user: currentUser,
    });
    
    setReplyText('');
    setReplyTo(null);
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const renderComment = (comment, depth = 0) => {
    const replies = comments.filter(c => c.parentId === comment.id);
    
    return (
      <div key={comment.id} style={{ marginLeft: depth > 0 ? '40px' : 0 }}>
        <div style={{
          display: 'flex',
          gap: '12px',
          padding: '12px',
          background: 'var(--ea-bg-hover)',
          borderRadius: '8px',
          marginBottom: '8px',
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'var(--ea-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            flexShrink: 0,
          }}>
            <User size={16} />
          </div>
          
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                {comment.user?.name || 'Anonymous'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>
                {formatTime(comment.timestamp)}
              </span>
            </div>
            
            <p style={{ margin: '0 0 8px', fontSize: '0.9rem', lineHeight: 1.5, color: 'var(--ea-text-primary)' }}>
              {comment.text}
            </p>
            
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                onClick={() => onLikeComment?.(comment.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.8rem',
                  color: 'var(--ea-text-secondary)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                }}
              >
                <ThumbsUp size={14} />
                {comment.likes || 0}
              </button>
              
              <button
                onClick={() => setReplyTo(comment.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.8rem',
                  color: 'var(--ea-text-secondary)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                }}
              >
                <Reply size={14} />
                Reply
              </button>
              
              {currentUser?.id === comment.user?.id && (
                <button
                  onClick={() => onDeleteComment?.(comment.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    color: 'var(--ea-danger)',
                    padding: '4px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Delete
                </button>
              )}
            </div>
            
            {replyTo === comment.id && (
              <form onSubmit={handleReplySubmit} style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Write a reply..."
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    background: 'var(--ea-bg)',
                    border: '1px solid var(--ea-border)',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    color: 'var(--ea-text-primary)',
                  }}
                />
                <button
                  type="submit"
                  className="ea-btn ea-btn-primary"
                  style={{ padding: '8px 12px' }}
                >
                  <Send size={14} />
                </button>
              </form>
            )}
          </div>
        </div>
        
        {replies.map(reply => renderComment(reply, depth + 1))}
      </div>
    );
  };

  return (
    <div style={{
      background: 'var(--ea-bg)',
      borderRadius: 'var(--ea-radius-lg)',
      border: '1px solid var(--ea-border)',
      padding: '20px',
      maxHeight: '600px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <MessageSquare size={20} color="var(--ea-primary)" />
        Comments ({comments.length})
      </h3>
      
      <div style={{ flex: 1, overflow: 'auto', marginBottom: '16px' }}>
        {comments.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            color: 'var(--ea-text-secondary)',
          }}>
            <MessageSquare size={48} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <p>No comments yet. Start the conversation!</p>
          </div>
        ) : (
          comments.filter(c => !c.parentId).map(comment => renderComment(comment))
        )}
        <div ref={commentsEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} style={{
        display: 'flex',
        gap: '8px',
        paddingTop: '16px',
        borderTop: '1px solid var(--ea-border)',
      }}>
        <input
          type="text"
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
          style={{
            flex: 1,
            padding: '10px 12px',
            background: 'var(--ea-bg-card)',
            border: '1px solid var(--ea-border)',
            borderRadius: '6px',
            fontSize: '0.9rem',
            color: 'var(--ea-text-primary)',
          }}
        />
        <button
          type="submit"
          className="ea-btn ea-btn-primary"
          disabled={!newComment.trim()}
          style={{ padding: '10px 16px' }}
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}

// Sharing Component
export function ShareDialog({ isOpen, onClose, shareUrl, onCopyLink, onEmailShare }) {
  const [copied, setCopied] = useState(false);
  const [email, setEmail] = useState('');
  const [permission, setPermission] = useState('view');

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      onCopyLink?.();
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleEmailShare = (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    onEmailShare?.(email, permission);
    setEmail('');
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      padding: '20px',
      backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        background: 'var(--ea-bg-card)',
        borderRadius: 'var(--ea-radius-lg)',
        padding: '24px',
        maxWidth: '500px',
        width: '100%',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        border: '1px solid var(--ea-border)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}>
          <h3 style={{ margin: 0, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Share2 size={20} color="var(--ea-primary)" />
            Share
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '50%',
              color: 'var(--ea-text-secondary)',
            }}
          >
            ✕
          </button>
        </div>

        {/* Share Link */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
            Share Link
          </label>
          <div style={{
            display: 'flex',
            gap: '8px',
            padding: '8px',
            background: 'var(--ea-bg-hover)',
            borderRadius: '6px',
            border: '1px solid var(--ea-border)',
          }}>
            <input
              type="text"
              value={shareUrl}
              readOnly
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                color: 'var(--ea-text-primary)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
            <button
              onClick={handleCopy}
              style={{
                background: 'var(--ea-primary)',
                border: 'none',
                borderRadius: '4px',
                padding: '6px 12px',
                color: 'white',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.8rem',
              }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Email Share */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
            Share via Email
          </label>
          <form onSubmit={handleEmailShare} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@example.com"
              style={{
                padding: '10px 12px',
                background: 'var(--ea-bg-hover)',
                border: '1px solid var(--ea-border)',
                borderRadius: '6px',
                fontSize: '0.9rem',
                color: 'var(--ea-text-primary)',
              }}
            />
            <select
              value={permission}
              onChange={(e) => setPermission(e.target.value)}
              style={{
                padding: '10px 12px',
                background: 'var(--ea-bg-hover)',
                border: '1px solid var(--ea-border)',
                borderRadius: '6px',
                fontSize: '0.9rem',
                color: 'var(--ea-text-primary)',
              }}
            >
              <option value="view">Can view</option>
              <option value="edit">Can edit</option>
              <option value="admin">Can administer</option>
            </select>
            <button
              type="submit"
              className="ea-btn ea-btn-primary"
              disabled={!email.trim()}
              style={{ width: '100%' }}
            >
              Send Invitation
            </button>
          </form>
        </div>

        {/* Quick Actions */}
        <div style={{
          padding: '12px',
          background: 'var(--ea-bg-hover)',
          borderRadius: '8px',
          fontSize: '0.85rem',
          color: 'var(--ea-text-secondary)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <ExternalLink size={14} />
            <span>Anyone with the link can access this report</span>
          </div>
          <div style={{ fontSize: '0.75rem' }}>
            Link expires in 30 days
          </div>
        </div>
      </div>
    </div>
  );
}