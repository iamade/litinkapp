import React from 'react';
import { Link } from 'react-router-dom';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

const Logo: React.FC<LogoProps> = ({ className = '', showText = true }) => {
  return (
    <Link to="/" className={`flex items-center gap-3 group ${className}`}>
      <div className="relative w-10 h-10 flex items-center justify-center">
        {/* Glow effect behind the logo */}
        <div className="absolute inset-0 bg-yellow-400/20 blur-xl opacity-50 group-hover:opacity-80 transition-opacity duration-300 rounded-full"></div>
        
        {/* Logo Image */}
        <img 
          src="/litink.png" 
          alt="Litink AI" 
          className="relative w-full h-full object-contain filter drop-shadow-lg transition-transform duration-300 group-hover:scale-110"
        />
      </div>
      
      {showText && (
        <span className="font-bold text-2xl tracking-tight text-white">
          LitinkAI
        </span>
      )}
    </Link>
  );
};

export default Logo;
