import { useState } from 'react'
import './TutorialModal.css'

interface Props {
  onClose: () => void
  onGetStarted?: () => void
}

interface TutorialStep {
  title: string
  content: React.ReactNode
  image?: string  // Path to image/gif
}

const tutorialSteps: TutorialStep[] = [
  {
    title: "Welcome to Entailment Trees",
    content: (
      <>
        <p>
          This tool helps you <strong>rigorously evaluate ideas</strong> by breaking them down
          into logical claims and testing them with simulations and literature.
        </p>
        <p>
          Instead of hand-wavy feasibility assessments, you build a <strong>logical tree</strong> where:
        </p>
        <ul>
          <li>Each claim gets a score (0-10) based on evidence</li>
          <li>Scores propagate from leaves up to your hypothesis</li>
          <li>You see exactly <em>why</em> an idea succeeds or fails</li>
        </ul>
        <p>
          The AI assistant helps you write simulations, search literature, and organize
          your findings into a structured argument.
        </p>
      </>
    ),
  },
  {
    title: "Claim Nodes",
    content: (
      <>
        <p>
          <strong>Claims</strong> are statements that can be evaluated as true or false.
          Each claim has a score from 0 (false) to 10 (true).
        </p>
        <p>
          The node color is a <strong>continuous scale</strong> from red (0) through
          yellow (5) to green (10), reflecting the claim's truth value.
        </p>
        <div className="tutorial-feature-list">
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: 'linear-gradient(to right, #f85149, #f8d922, #3fb950)', color: 'transparent' }}>.</span>
            <span>Color scale: Red → Yellow → Green (0 → 5 → 10)</span>
          </div>
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#808080' }}>?</span>
            <span>Gray = No evidence (defaults to score 5, unsure)</span>
          </div>
        </div>
        <p><strong>Interactions:</strong></p>
        <ul>
          <li><strong>Double-click</strong> a node to select it and see details</li>
          <li><strong>Hold + drag</strong> to move nodes around</li>
          <li><strong>+/- button</strong> to collapse/expand subtrees</li>
        </ul>
        <p>
          When selected, the right panel shows the claim's evidence, score reasoning,
          and any uncertainties.
        </p>
      </>
    ),
  },
  {
    title: "Implication Edges",
    content: (
      <>
        <p>
          <strong>Implications</strong> connect claims with logical relationships:
          "If premises are true, then conclusion is true."
        </p>
        <div className="tutorial-feature-list">
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#58a6ff' }}>∧</span>
            <span><strong>AND</strong> — All premises must be true for conclusion to follow</span>
          </div>
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#d29922' }}>∨</span>
            <span><strong>OR</strong> — Any single premise being true is sufficient</span>
          </div>
        </div>
        <p><strong>Edge Colors:</strong></p>
        <ul>
          <li><span style={{ color: '#3fb950' }}>Green</span> = Entailment is logically valid</li>
          <li><span style={{ color: '#f85149' }}>Red</span> = Entailment failed validation</li>
          <li><span style={{ color: '#848d97' }}>Gray</span> = Not yet checked</li>
        </ul>
        <p>
          Click the small junction node (where edges meet) to see the logical
          justification for why the premises entail the conclusion.
        </p>
      </>
    ),
  },
  {
    title: "Cost Propagation",
    content: (
      <>
        <p>
          Costs <strong>propagate from leaves up to the hypothesis</strong> using a
          negative-log formula that combines uncertainty:
        </p>
        <div className="tutorial-formula">
          <div><strong>AND:</strong> cost = Σ(-log(score/10))</div>
          <div><strong>OR:</strong> cost = min(-log(score/10))</div>
        </div>
        <p>
          Lower cost = higher confidence. A cost of 0 means perfect certainty.
        </p>
        <p>
          When viewing costs, each claim also shows the <strong>inferred probability</strong>:
        </p>
        <div className="tutorial-formula">
          <div>P = 2<sup>-cost</sup></div>
        </div>
        <p>
          Use the <strong>View: Score/Cost</strong> dropdown in the header to switch
          between viewing raw scores vs propagated costs.
        </p>
      </>
    ),
  },
  {
    title: "Getting Started",
    content: (
      <>
        <p>
          Ready to evaluate your idea? Here's the workflow:
        </p>
        <div className="tutorial-feature-list">
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#58a6ff' }}>1</span>
            <span><strong>Chat</strong> — Describe your hypothesis and the AI breaks it into testable claims</span>
          </div>
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#3fb950' }}>2</span>
            <span><strong>Investigate</strong> — The AI writes simulations and searches literature for evidence</span>
          </div>
          <div className="tutorial-feature">
            <span className="feature-icon" style={{ background: '#d29922' }}>3</span>
            <span><strong>Watch</strong> — Your entailment tree grows as evidence accumulates</span>
          </div>
        </div>
        <p style={{ marginTop: '16px', textAlign: 'center' }}>
          Click <strong>Get Started</strong> to create your first approach.
        </p>
      </>
    ),
  },
]

function TutorialModal({ onClose, onGetStarted }: Props) {
  const [currentStep, setCurrentStep] = useState(0)

  const step = tutorialSteps[currentStep]
  const isFirst = currentStep === 0
  const isLast = currentStep === tutorialSteps.length - 1

  return (
    <div className="tutorial-overlay" onClick={onClose}>
      <div className="tutorial-modal" onClick={(e) => e.stopPropagation()}>
        <button className="tutorial-close" onClick={onClose}>×</button>

        <div className="tutorial-progress">
          {tutorialSteps.map((_, i) => (
            <div
              key={i}
              className={`progress-dot ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'completed' : ''}`}
              onClick={() => setCurrentStep(i)}
            />
          ))}
        </div>

        <h2>{step.title}</h2>

        {step.image && (
          <div className="tutorial-image">
            <img src={step.image} alt={step.title} />
          </div>
        )}

        <div className="tutorial-content">
          {step.content}
        </div>

        <div className="tutorial-nav">
          <button
            className="tutorial-nav-btn"
            onClick={() => setCurrentStep(s => s - 1)}
            disabled={isFirst}
          >
            ← Back
          </button>

          <span className="tutorial-step-indicator">
            {currentStep + 1} / {tutorialSteps.length}
          </span>

          {isLast ? (
            <button className="tutorial-nav-btn primary" onClick={onGetStarted || onClose}>
              Get Started
            </button>
          ) : (
            <button
              className="tutorial-nav-btn primary"
              onClick={() => setCurrentStep(s => s + 1)}
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default TutorialModal
