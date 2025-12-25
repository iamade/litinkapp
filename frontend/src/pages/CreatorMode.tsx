import CreatorStudio from "../components/Dashboard/CreatorStudio";
import { useAuth, hasAnyRole } from "../contexts/AuthContext";
import React from 'react';

export default function CreatorMode() {
  const { user } = useAuth();

  if (!user || !hasAnyRole(user, ["creator", "author"])) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">Creator access required</p>
          <p className="text-gray-500">Please add the creator profile to your account to create content.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <CreatorStudio />
      </div>
    </div>
  );
}