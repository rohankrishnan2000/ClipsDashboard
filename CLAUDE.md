# Claude Instructions

## Plugins

Use relevant plugins whenever they are available and appropriate for the task. Prefer plugin-provided tools, workflows, and instructions over ad hoc approaches when they directly apply.

## Screenshot Rule

When building or modifying a website or frontend app running on localhost, use Puppeteer to inspect it visually at important points in the workflow.

- Start or use the local dev server for the site.
- Open the localhost URL with Puppeteer.
- Take screenshots after meaningful UI changes, layout work, interaction changes, and before considering the work complete.
- Review the screenshots for correctness, including layout, spacing, text overflow, responsive behavior, visual regressions, and whether the page matches the intended result.
- If the screenshot reveals an issue, fix the implementation and screenshot again.
- Repeat this loop until the UI is visually verified.
