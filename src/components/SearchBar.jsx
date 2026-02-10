// Placeholder component - will be implemented in later tasks
export default function SearchBar() {
  return (
    <div className="w-full mb-4">
      <input
        type="text"
        placeholder="Search recipes..."
        className="w-full p-2 border border-gray-300 rounded-md"
        disabled
      />
    </div>
  )
}