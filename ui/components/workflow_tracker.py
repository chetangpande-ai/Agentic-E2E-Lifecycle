"""
Visual workflow progress tracker component.
Shows the multi-step STLC pipeline with animated status.
"""

import streamlit as st

WORKFLOW_STEPS = [
    {"id": 0, "label": "Requirements", "icon": "📥", "key": "requirements"},
    {"id": 1, "label": "Analysis", "icon": "🔍", "key": "analysis"},
    {"id": 2, "label": "Test Cases", "icon": "📝", "key": "testcases"},
    {"id": 3, "label": "Scripts", "icon": "💻", "key": "scripts"},
    {"id": 4, "label": "Execution", "icon": "🚀", "key": "execution"},
    {"id": 5, "label": "PR/Commit", "icon": "📤", "key": "commit"},
]


def render_workflow_tracker(current_step: int = 0, rejected_step: int = -1):
    """
    Render the horizontal workflow progress tracker.
    
    Args:
        current_step: Index of the currently active step (0-5).
        rejected_step: Index of the rejected step (-1 if none).
    """
    steps_html = ""

    for i, step in enumerate(WORKFLOW_STEPS):
        # Determine step state
        if rejected_step == i:
            state_class = "rejected"
            icon = "✕"
        elif i < current_step:
            state_class = "completed"
            icon = "✓"
        elif i == current_step:
            state_class = "active"
            icon = step["icon"]
        else:
            state_class = "pending"
            icon = step["icon"]

        steps_html += f"""
        <div class="step">
            <div class="step-icon {state_class}">{icon}</div>
            <span class="step-label">{step['label']}</span>
        </div>
        """

        # Add connector between steps (except after last)
        if i < len(WORKFLOW_STEPS) - 1:
            connector_class = "completed" if i < current_step else ""
            steps_html += f'<div class="step-connector {connector_class}"></div>'

    st.markdown(f"""
    <div class="workflow-tracker">
        {steps_html}
    </div>
    """, unsafe_allow_html=True)
