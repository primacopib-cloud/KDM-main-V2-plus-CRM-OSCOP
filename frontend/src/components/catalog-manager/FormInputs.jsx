import { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';

// Section wrapper
export const FormSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-white/[0.08] rounded-xl overflow-hidden mb-4">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-3 flex items-center justify-between bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-[#D9B35A]" />}
          <span className="font-medium text-white text-sm">{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>
      {isOpen && (
        <div className="p-4 space-y-4 border-t border-white/[0.08]">
          {children}
        </div>
      )}
    </div>
  );
};

// Tag input component
export const TagInput = ({ value = [], onChange, placeholder }) => {
  const [input, setInput] = useState('');
  
  const addTag = () => {
    if (input.trim() && !value.includes(input.trim())) {
      onChange([...value, input.trim()]);
      setInput('');
    }
  };
  
  const removeTag = (tag) => {
    onChange(value.filter(t => t !== tag));
  };
  
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
          placeholder={placeholder}
          className="flex-1 bg-white/[0.04] border-white/10 text-white text-sm"
        />
        <Button type="button" size="sm" onClick={addTag} variant="outline" className="border-white/10">
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((tag) => (
            <Badge key={`tag-${tag}`} variant="outline" className="bg-white/[0.04] border-white/10 text-xs">
              {tag}
              <button type="button" onClick={() => removeTag(tag)} className="ml-1 hover:text-red-400">
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};
