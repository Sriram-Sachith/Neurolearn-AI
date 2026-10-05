export type TokenPayload = {
  access_token: string;
  name: string;
  email: string;
};

export type DocumentItem = {
  id: string;
  filename: string;
  original_name: string;
  status: string;
  size_bytes: number;
  created_at: string;
};

export type Job = {
  id: string;
  document_id: string;
  status: string;
  progress: number;
  error_message: string;
  model_name: string;
};

export type Note = {
  id: string;
  title: string;
  content: string;
  source_pages: string;
  model_name: string;
};

export type Evidence = {
  chunk_id: string;
  support_status: string;
  score: number;
  passage: string;
  page_number: number;
};

export type Flashcard = {
  id: string;
  question: string;
  answer: string;
  card_type: string;
  difficulty: string;
  source_pages: string;
  support_status: string;
  model_name: string;
  evidence: Evidence[];
};

export type Topic = {
  id: string;
  topic_name: string;
  cluster_id: number | null;
  keywords: string;
};

export type QuizItem = {
  id: string;
  question: string;
  qtype: string;
  options: string[];
  explanation: string;
  topic_name: string;
  difficulty: string;
  source_pages: string;
};

export type Quiz = {
  id: string;
  title: string;
  items: QuizItem[];
};

export type RevisionCard = {
  card_id: string;
  question: string;
  answer: string;
  difficulty: string;
  support_status: string;
  n: number;
  ef: number;
};
