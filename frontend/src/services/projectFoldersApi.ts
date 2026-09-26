/**
 * Projets tenus dans des dossiers du Mac (une fiche .md par dossier).
 */

import api from './api';

export interface FolderEntry {
  name: string;
  path: string;
  is_project: boolean;
}

export interface BrowseResult {
  path: string;
  display: string;
  parent: string | null;
  breadcrumb: { name: string; path: string }[];
  dirs: FolderEntry[];
  files: { name: string; is_md: boolean }[];
}

export interface SyncReport {
  created: string[];
  updated: string[];
  checked: string[];
  exported: string[];
  kept: string[];
  warnings: string[];
}

export interface ProjectsFolderState {
  available: boolean;
  root_display: string;
  path: string | null;
  display: string | null;
  projects: { folder: string; file: string; path: string }[];
  report?: SyncReport | null;
}

export const projectFoldersApi = {
  get: async (): Promise<ProjectsFolderState> =>
    (await api.get<ProjectsFolderState>('/settings/projects-folder')).data,

  browse: async (path = ''): Promise<BrowseResult> =>
    (await api.get<BrowseResult>('/settings/projects-folder/browse', { params: { path } })).data,

  set: async (path: string | null): Promise<ProjectsFolderState> =>
    (await api.put<ProjectsFolderState>('/settings/projects-folder', { path })).data,

  sync: async (): Promise<SyncReport> =>
    (await api.post<SyncReport>('/settings/projects-folder/sync')).data,

  importMarkdown: async (file: File): Promise<{ id: number; name: string; source_path: string | null }> => {
    const form = new FormData();
    form.append('file', file);
    return (
      await api.post('/projects/import-md', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    ).data;
  },
};
