from vulture.core.cv_parser import parse_cv_text
from vulture.core.question_templates import generate_question_templates


def test_cv_parser_extracts_key_sections_and_links() -> None:
    sample = r"""
\begin{rSection}{Summary}
AI researcher focused on ML systems.
\end{rSection}

\begin{rSection}{Education}
{\bf Physics, PhD} \\
Advisor: Prof. Example
\end{rSection}

\begin{rSection}{Publications & Preprints}
\begin{itemize}
\item Example et al. \href{https://doi.org/10.1000/test}{doi link}
\end{itemize}
\end{rSection}
"""
    parsed = parse_cv_text(sample, input_format="latex")
    assert "summary" in parsed.sections
    assert "education" in parsed.sections
    assert "publications" in parsed.sections
    assert parsed.metadata["all_links"]


def test_question_template_generator_reaches_large_questionnaire_target() -> None:
    sample = r"""
\begin{rSection}{Summary}
Systems + ML engineer.
\end{rSection}
\begin{rSection}{Technical Skills}
Programming Languages: Python, C++, CUDA, OpenCL
Machine Learning: PyTorch, TensorFlow, Transformers, DBSCAN
\end{rSection}
\begin{rSection}{Research Experience}
\begin{itemize}
\item Built scalable transformers
\item Developed HPC workflows with SLURM
\end{itemize}
\end{rSection}
\begin{rSection}{Publications & Preprints}
\begin{itemize}
\item Paper A
\item Paper B
\end{itemize}
\end{rSection}
\begin{rSection}{Awards & Honors}
\begin{itemize}
\item NSF travel award
\end{itemize}
\end{rSection}
\begin{rSection}{Presentations & Conferences}
\begin{itemize}
\item FNANO 2025
\end{itemize}
\end{rSection}
\begin{rSection}{Teaching & Mentoring Experience}
\begin{itemize}
\item TA role
\end{itemize}
\end{rSection}
\begin{rSection}{Service & Outreach}
\begin{itemize}
\item Outreach event
\end{itemize}
\end{rSection}
\begin{rSection}{Additional Projects}
\begin{itemize}
\item OpenCL scheduler
\end{itemize}
\end{rSection}
"""
    parsed = parse_cv_text(sample, input_format="latex")
    templates = generate_question_templates(parsed, scope="all")
    assert len(templates) >= 120
