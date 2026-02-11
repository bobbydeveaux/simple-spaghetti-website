import React, { useState } from 'react';
import { useVoting } from '../context/VotingContext';

const BallotCard = ({ ballot }) => {
  const {
    submitVote,
    loading,
    getUserVoteForBallot,
    canUserVoteOnBallot,
    getRemainingVotesForBallot,
    setError
  } = useVoting();

  const [selectedOption, setSelectedOption] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const userVotes = getUserVoteForBallot(ballot.id);
  const canVote = canUserVoteOnBallot(ballot);
  const remainingVotes = getRemainingVotesForBallot(ballot);

  const handleVoteSubmit = async (e) => {
    e.preventDefault();
    if (!selectedOption) {
      setError('Please select an option to vote for');
      return;
    }

    setIsSubmitting(true);
    try {
      await submitVote(ballot.id, parseInt(selectedOption));
      setSelectedOption(''); // Reset selection after successful vote
      setError(null);
    } catch (err) {
      console.error('Vote submission failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      {/* Ballot Header */}
      <div className="mb-4">
        <h3 className="text-xl font-bold text-gray-900 mb-2">{ballot.title}</h3>
        <p className="text-gray-600 mb-3">{ballot.description}</p>

        <div className="text-sm text-gray-500 space-y-1">
          <p>🗓️ Voting Period: {formatDate(ballot.start_date)} - {formatDate(ballot.end_date)}</p>
          <p>🗳️ Max votes per member: {ballot.max_votes_per_member}</p>
          {userVotes.length > 0 && (
            <p>✅ Your votes used: {userVotes.length}/{ballot.max_votes_per_member}</p>
          )}
          {remainingVotes > 0 && (
            <p className="text-blue-600 font-medium">
              🔥 You have {remainingVotes} vote{remainingVotes === 1 ? '' : 's'} remaining
            </p>
          )}
        </div>
      </div>

      {/* User's Previous Votes */}
      {userVotes.length > 0 && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <h4 className="text-sm font-medium text-green-800 mb-2">Your Previous Votes:</h4>
          <ul className="text-sm text-green-700 space-y-1">
            {userVotes.map((vote, index) => (
              <li key={index}>
                ✓ {vote.option_title} <span className="text-green-600">({new Date(vote.timestamp).toLocaleString()})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Voting Form */}
      {canVote ? (
        <form onSubmit={handleVoteSubmit} className="space-y-3">
          <div className="space-y-2">
            {ballot.options.map((option) => (
              <label key={option.id} className="flex items-start space-x-3 p-3 border rounded-md hover:bg-gray-50 cursor-pointer">
                <input
                  type="radio"
                  name={`ballot-${ballot.id}`}
                  value={option.id}
                  checked={selectedOption === option.id.toString()}
                  onChange={(e) => setSelectedOption(e.target.value)}
                  className="mt-1 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{option.title}</div>
                  <div className="text-sm text-gray-600 mt-1">{option.description}</div>
                </div>
              </label>
            ))}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || loading || !selectedOption}
            className={`w-full py-2 px-4 rounded-md font-medium ${
              isSubmitting || loading || !selectedOption
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            } text-white transition-colors duration-200`}
          >
            {isSubmitting ? 'Submitting Vote...' : 'Submit Vote'}
          </button>
        </form>
      ) : (
        <div className="text-center py-4">
          {userVotes.length >= ballot.max_votes_per_member ? (
            <div className="text-green-600 font-medium">
              ✅ You have used all your votes for this ballot
            </div>
          ) : (
            <div className="text-gray-500">
              Voting not available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BallotCard;