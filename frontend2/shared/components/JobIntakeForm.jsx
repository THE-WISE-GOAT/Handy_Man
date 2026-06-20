import React, { useMemo, useState } from 'react';

export const JOB_INTAKE_CATEGORIES = [
  { value: 'plumbing', label: 'Plumbing', description: 'Leaks, clogs, pipe bursts, pressure drops' },
  { value: 'electrical', label: 'Electrical', description: 'Outlets, wiring, breakers, lighting failures' },
  { value: 'hvac', label: 'HVAC', description: 'Cooling, heating, airflow, thermostat issues' },
  { value: 'appliance_repair', label: 'Appliance Repair', description: 'Washers, ovens, refrigerators, and more' },
  { value: 'other', label: 'Other', description: 'Anything not covered above' }
];

export const JOB_INTAKE_URGENCY_LEVELS = [
  { value: 'low', label: 'Low', description: 'Convenience issue, no immediate risk' },
  { value: 'medium', label: 'Medium', description: 'Needs attention soon, but can wait today' },
  { value: 'high', label: 'High', description: 'Safety risk, active damage, or urgent outage' }
];

export const DEFAULT_JOB_INTAKE_VALUES = {
  problem_category: 'plumbing',
  detailed_problem: '',
  urgency_level: 'medium'
};

const createEmptyErrors = () => ({
  problem_category: '',
  detailed_problem: '',
  urgency_level: ''
});

const buildPayload = (formState) => ({
  problem_category: formState.problem_category,
  detailed_problem: formState.detailed_problem.trim(),
  urgency_level: formState.urgency_level
});

export default function JobIntakeForm({
  initialValues = DEFAULT_JOB_INTAKE_VALUES,
  onSubmit,
  onChange,
  submitLabel = 'Analyze problem',
  title = 'Job Intake',
  subtitle = 'Capture the issue in the exact shape the AI extraction pipeline expects.',
  className = '',
  disabled = false
}) {
  const [formState, setFormState] = useState({
    ...DEFAULT_JOB_INTAKE_VALUES,
    ...initialValues
  });
  const [errors, setErrors] = useState(createEmptyErrors());
  const [touched, setTouched] = useState({
    problem_category: false,
    detailed_problem: false,
    urgency_level: false
  });

  const selectedCategory = useMemo(
    () => JOB_INTAKE_CATEGORIES.find((category) => category.value === formState.problem_category),
    [formState.problem_category]
  );

  const selectedUrgency = useMemo(
    () => JOB_INTAKE_URGENCY_LEVELS.find((level) => level.value === formState.urgency_level),
    [formState.urgency_level]
  );

  const setFieldValue = (field, value) => {
    const nextState = { ...formState, [field]: value };
    setFormState(nextState);
    onChange?.(nextState);
  };

  const validate = () => {
    const nextErrors = createEmptyErrors();
    let isValid = true;

    if (!formState.problem_category) {
      nextErrors.problem_category = 'Choose a problem category.';
      isValid = false;
    }

    if (!formState.detailed_problem.trim()) {
      nextErrors.detailed_problem = 'Describe what is happening.';
      isValid = false;
    } else if (formState.detailed_problem.trim().length < 20) {
      nextErrors.detailed_problem = 'Add a little more detail so the AI can summarize accurately.';
      isValid = false;
    }

    if (!formState.urgency_level) {
      nextErrors.urgency_level = 'Pick an urgency level.';
      isValid = false;
    }

    setErrors(nextErrors);
    return isValid;
  };

  const handleBlur = (field) => {
    setTouched((current) => ({ ...current, [field]: true }));
    validate();
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!validate()) {
      return;
    }

    onSubmit?.(buildPayload(formState));
  };

  const payloadPreview = buildPayload(formState);
  const canSubmit = !disabled && payloadPreview.detailed_problem.length >= 20;

  return (
    <section className={`job-intake ${className}`.trim()} aria-labelledby="job-intake-title">
      <div className="job-intake__shell">
        <header className="job-intake__hero">
          <div className="job-intake__eyebrow">AI-Ready Dispatch Intake</div>
          <h2 id="job-intake-title" className="job-intake__title">{title}</h2>
          <p className="job-intake__subtitle">{subtitle}</p>
        </header>

        <form className="job-intake__form" onSubmit={handleSubmit} noValidate>
          <div className="job-intake__grid">
            <div className="job-intake__field job-intake__field--full">
              <label className="job-intake__label" htmlFor="problem_category">Problem category</label>
              <select
                id="problem_category"
                name="problem_category"
                className="job-intake__select"
                value={formState.problem_category}
                onChange={(event) => setFieldValue('problem_category', event.target.value)}
                onBlur={() => handleBlur('problem_category')}
                aria-invalid={Boolean(touched.problem_category && errors.problem_category)}
              >
                {JOB_INTAKE_CATEGORIES.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
              <p className="job-intake__helper">{selectedCategory?.description}</p>
              {touched.problem_category && errors.problem_category ? (
                <p className="job-intake__error">{errors.problem_category}</p>
              ) : null}
            </div>

            <div className="job-intake__field job-intake__field--full">
              <label className="job-intake__label" htmlFor="detailed_problem">Detailed problem</label>
              <textarea
                id="detailed_problem"
                name="detailed_problem"
                className="job-intake__textarea"
                rows={7}
                value={formState.detailed_problem}
                onChange={(event) => setFieldValue('detailed_problem', event.target.value)}
                onBlur={() => handleBlur('detailed_problem')}
                placeholder="Example: Kitchen sink is leaking from the P-trap and the cabinet floor is wet after every use."
                aria-invalid={Boolean(touched.detailed_problem && errors.detailed_problem)}
              />
              <div className="job-intake__meta-row">
                <p className="job-intake__helper">
                  The backend schema wants a concise summary of the actual fault and symptoms.
                </p>
                <span className="job-intake__counter">{formState.detailed_problem.trim().length} chars</span>
              </div>
              {touched.detailed_problem && errors.detailed_problem ? (
                <p className="job-intake__error">{errors.detailed_problem}</p>
              ) : null}
            </div>

            <fieldset className="job-intake__field job-intake__field--full">
              <legend className="job-intake__label">Urgency level</legend>
              <div className="job-intake__radio-grid" role="radiogroup" aria-label="Urgency level">
                {JOB_INTAKE_URGENCY_LEVELS.map((level) => (
                  <label key={level.value} className={`job-intake__radio-card ${formState.urgency_level === level.value ? 'is-selected' : ''}`}>
                    <input
                      type="radio"
                      name="urgency_level"
                      value={level.value}
                      checked={formState.urgency_level === level.value}
                      onChange={(event) => setFieldValue('urgency_level', event.target.value)}
                      onBlur={() => handleBlur('urgency_level')}
                    />
                    <span className="job-intake__radio-title">{level.label}</span>
                    <span className="job-intake__radio-description">{level.description}</span>
                  </label>
                ))}
              </div>
              <p className="job-intake__helper">{selectedUrgency?.description}</p>
              {touched.urgency_level && errors.urgency_level ? (
                <p className="job-intake__error">{errors.urgency_level}</p>
              ) : null}
            </fieldset>
          </div>

          <div className="job-intake__preview">
            <div className="job-intake__preview-header">
              <span className="job-intake__preview-badge">Schema Preview</span>
              <span className="job-intake__preview-note">Ready for CustomerProblemSchema</span>
            </div>
            <pre className="job-intake__json" aria-label="JSON preview">
{JSON.stringify(payloadPreview, null, 2)}
            </pre>
          </div>

          <div className="job-intake__actions">
            <button type="submit" className="job-intake__submit" disabled={!canSubmit}>
              {submitLabel}
            </button>
          </div>
        </form>
      </div>

      <style>{`
        .job-intake {
          width: 100%;
          display: grid;
          place-items: center;
          padding: 24px;
        }

        .job-intake__shell {
          width: min(100%, 960px);
          background: linear-gradient(180deg, rgba(10, 18, 32, 0.98) 0%, rgba(15, 23, 42, 0.96) 100%);
          border: 1px solid rgba(148, 163, 184, 0.22);
          border-radius: 24px;
          box-shadow: 0 24px 80px rgba(15, 23, 42, 0.35);
          padding: 28px;
          color: #e2e8f0;
        }

        .job-intake__hero {
          margin-bottom: 20px;
        }

        .job-intake__eyebrow {
          display: inline-flex;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #93c5fd;
          background: rgba(37, 99, 235, 0.14);
          border: 1px solid rgba(96, 165, 250, 0.28);
          margin-bottom: 14px;
        }

        .job-intake__title {
          margin: 0;
          font-size: clamp(1.8rem, 4vw, 2.6rem);
          line-height: 1.05;
          color: #f8fafc;
        }

        .job-intake__subtitle {
          margin: 12px 0 0;
          max-width: 62ch;
          color: #cbd5e1;
          line-height: 1.6;
        }

        .job-intake__form {
          display: grid;
          gap: 20px;
        }

        .job-intake__grid {
          display: grid;
          gap: 18px;
          grid-template-columns: 1fr;
        }

        .job-intake__field {
          display: grid;
          gap: 10px;
        }

        .job-intake__field--full {
          width: 100%;
        }

        .job-intake__label {
          font-size: 14px;
          font-weight: 700;
          color: #f8fafc;
        }

        .job-intake__select,
        .job-intake__textarea {
          width: 100%;
          border-radius: 16px;
          border: 1px solid rgba(148, 163, 184, 0.24);
          background: rgba(15, 23, 42, 0.72);
          color: #f8fafc;
          padding: 14px 16px;
          font: inherit;
          outline: none;
          transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
        }

        .job-intake__textarea {
          resize: vertical;
          min-height: 168px;
        }

        .job-intake__select:focus,
        .job-intake__textarea:focus,
        .job-intake__radio-card input:focus-visible {
          border-color: rgba(96, 165, 250, 0.9);
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.18);
        }

        .job-intake__helper {
          margin: 0;
          color: #94a3b8;
          font-size: 13px;
          line-height: 1.5;
        }

        .job-intake__meta-row {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
        }

        .job-intake__counter {
          flex-shrink: 0;
          color: #cbd5e1;
          font-size: 12px;
          padding: 4px 8px;
          border-radius: 999px;
          background: rgba(30, 41, 59, 0.72);
          border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .job-intake__error {
          margin: 0;
          color: #fca5a5;
          font-size: 13px;
        }

        .job-intake__radio-grid {
          display: grid;
          gap: 12px;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }

        .job-intake__radio-card {
          display: grid;
          gap: 6px;
          padding: 14px;
          border-radius: 18px;
          border: 1px solid rgba(148, 163, 184, 0.18);
          background: rgba(15, 23, 42, 0.72);
          cursor: pointer;
          transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
        }

        .job-intake__radio-card:hover {
          transform: translateY(-1px);
          border-color: rgba(96, 165, 250, 0.45);
        }

        .job-intake__radio-card.is-selected {
          border-color: rgba(96, 165, 250, 0.9);
          background: rgba(30, 41, 59, 0.92);
        }

        .job-intake__radio-card input {
          position: absolute;
          opacity: 0;
          pointer-events: none;
        }

        .job-intake__radio-title {
          font-weight: 700;
          color: #f8fafc;
        }

        .job-intake__radio-description {
          font-size: 13px;
          color: #cbd5e1;
          line-height: 1.45;
        }

        .job-intake__preview {
          border-radius: 20px;
          padding: 18px;
          background: rgba(2, 6, 23, 0.55);
          border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .job-intake__preview-header {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .job-intake__preview-badge {
          display: inline-flex;
          align-items: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(14, 165, 233, 0.14);
          border: 1px solid rgba(56, 189, 248, 0.25);
          color: #7dd3fc;
          font-size: 12px;
          font-weight: 700;
        }

        .job-intake__preview-note {
          color: #94a3b8;
          font-size: 12px;
        }

        .job-intake__json {
          margin: 0;
          padding: 16px;
          border-radius: 16px;
          background: rgba(15, 23, 42, 0.92);
          color: #dbeafe;
          overflow: auto;
          font-size: 13px;
          line-height: 1.55;
        }

        .job-intake__actions {
          display: flex;
          justify-content: flex-end;
        }

        .job-intake__submit {
          border: none;
          border-radius: 999px;
          padding: 14px 20px;
          font-weight: 800;
          letter-spacing: 0.02em;
          color: #081120;
          background: linear-gradient(135deg, #7dd3fc 0%, #93c5fd 100%);
          box-shadow: 0 12px 30px rgba(56, 189, 248, 0.22);
          cursor: pointer;
          transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
        }

        .job-intake__submit:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 16px 36px rgba(56, 189, 248, 0.28);
        }

        .job-intake__submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          box-shadow: none;
        }

        @media (min-width: 900px) {
          .job-intake__grid {
            grid-template-columns: 1fr 1fr;
            align-items: start;
          }

          .job-intake__field--full,
          .job-intake__preview,
          .job-intake__actions {
            grid-column: 1 / -1;
          }
        }
      `}</style>
    </section>
  );
}
