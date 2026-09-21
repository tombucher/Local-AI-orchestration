/**
 * API de l'espace documents d'un projet.
 */

import api from './api';
import type {
  DocumentTextCreate, DocumentUpdate, ProjectDocument, ProjectDocumentDetail,
} from '../types/document.types';

export const documentsApi = {
  list: async (projectId: number): Promise<ProjectDocument[]> => {
    const response = await api.get<ProjectDocument[]>(`/projects/${projectId}/documents`);
    return response.data;
  },

  /** Note ou extrait de code collé directement */
  addText: async (projectId: number, payload: DocumentTextCreate): Promise<ProjectDocument> => {
    const response = await api.post<ProjectDocument>(`/projects/${projectId}/documents/text`, payload);
    return response.data;
  },

  /** Fichier texte, code ou image */
  upload: async (projectId: number, file: File, note?: string): Promise<ProjectDocument> => {
    const form = new FormData();
    form.append('file', file);
    if (note) form.append('note', note);
    const response = await api.post<ProjectDocument>(`/projects/${projectId}/documents/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  get: async (projectId: number, id: number): Promise<ProjectDocumentDetail> => {
    const response = await api.get<ProjectDocumentDetail>(`/projects/${projectId}/documents/${id}`);
    return response.data;
  },

  update: async (projectId: number, id: number, payload: DocumentUpdate): Promise<ProjectDocument> => {
    const response = await api.patch<ProjectDocument>(`/projects/${projectId}/documents/${id}`, payload);
    return response.data;
  },

  remove: async (projectId: number, id: number): Promise<void> => {
    await api.delete(`/projects/${projectId}/documents/${id}`);
  },

  /**
   * Charge une image et renvoie une URL d'objet locale.
   * Une balise <img src> ne peut pas porter l'en-tête Authorization : il faut
   * donc récupérer les octets via axios, puis fabriquer un blob: URL.
   * L'appelant doit libérer l'URL avec URL.revokeObjectURL().
   */
  fetchImage: async (projectId: number, id: number): Promise<string> => {
    const response = await api.get(`/projects/${projectId}/documents/${id}/raw`, {
      responseType: 'blob',
      silentError: true,
    });
    return URL.createObjectURL(response.data as Blob);
  },
};
