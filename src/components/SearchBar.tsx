
import { Search } from 'lucide-react';

const SearchBar = () => {
  return (
    <div className="relative w-full max-w-lg">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Search className="h-4 w-4 text-gray-400" />
      </div>
      <input
        type="text"
        className="bg-gray-100 pl-10 pr-4 py-2 w-full rounded-full focus:outline-none focus:ring-2 focus:ring-neuro-blue"
        placeholder="Search..."
      />
    </div>
  );
};

export default SearchBar;
