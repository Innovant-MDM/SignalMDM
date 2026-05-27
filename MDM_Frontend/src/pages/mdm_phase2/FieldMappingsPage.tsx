import React from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/FieldMappingsPage.css';


/**
 * FieldMappingsPage component placeholder.
 * Handed over to the Frontend team for Phase 2 UI implementation.
 * 
 * Respective Service File for API access:
 * - src/services/mdm_phase2/mappingService.ts
 */
export const FieldMappingsPage: React.FC = () => {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Field Mappings</h1>
      <p className="mt-2 text-sm text-gray-500">
        Map source schemas fields to their corresponding canonical model fields.
      </p>
      <div className="mt-8 border border-dashed border-gray-300 rounded-lg p-12 text-center">
        <span className="text-gray-400">UI implementation pending (Assigned to frontend team)</span>
      </div>
    </div>
  );
};

export default FieldMappingsPage;
