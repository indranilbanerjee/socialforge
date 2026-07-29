#!/usr/bin/env node
/**
 * assemble_docx.js — Build the DOCX-ready JSON structure for calendar delivery documents.
 *
 * DOCX emission is NOT implemented: the `docx` npm package is not a shipped
 * dependency of this plugin. This script emits a fully structured JSON document
 * (title, summary, weekly sections, publishing schedule) that a DOCX writer —
 * or Claude itself — converts to .docx downstream. `docx_output` always reports
 * that no .docx file was written.
 */

const fs = require('fs');
const path = require('path');

// Storage precedence mirrors the Python scripts:
// ${CLAUDE_PLUGIN_DATA}/socialforge when it exists, else ~/socialforge-workspace
const WORKSPACE = (() => {
    const pluginData = process.env.CLAUDE_PLUGIN_DATA || '';
    if (pluginData && fs.existsSync(pluginData)) {
        return path.join(pluginData, 'socialforge');
    }
    return path.join(require('os').homedir(), 'socialforge-workspace');
})();

function buildDocxStructure(brand, month) {
    const monthDir = path.join(WORKSPACE, 'output', brand, month);
    const calendarPath = path.join(monthDir, 'calendar-data.json');
    const trackerPath = path.join(monthDir, 'status-tracker.json');

    if (!fs.existsSync(calendarPath)) {
        return { error: `Calendar not found: ${calendarPath}` };
    }

    const calendar = JSON.parse(fs.readFileSync(calendarPath, 'utf-8'));
    const tracker = fs.existsSync(trackerPath)
        ? JSON.parse(fs.readFileSync(trackerPath, 'utf-8'))
        : { posts: {} };

    // Build document structure
    const doc = {
        title: `${calendar.brand || brand} — Social Media Calendar`,
        subtitle: `${month}`,
        generated: new Date().toISOString(),
        sections: []
    };

    // Summary section
    const summary = calendar.summary || {};
    doc.sections.push({
        type: 'summary',
        title: 'Monthly Overview',
        content: {
            total_posts: summary.total_posts || calendar.posts?.length || 0,
            platforms: summary.posts_per_platform || {},
            tiers: summary.tier_distribution || {},
            content_types: summary.content_type_distribution || {}
        }
    });

    // Group posts by week
    const weeks = {};
    for (const post of (calendar.posts || [])) {
        const week = post.week_number || 1;
        if (!weeks[week]) weeks[week] = [];
        weeks[week].push(post);
    }

    // Weekly sections
    const weekEntries = Object.entries(weeks).sort((a, b) => Number(a[0]) - Number(b[0]));
    for (const [weekNum, posts] of weekEntries) {
        const weekSection = {
            type: 'week',
            title: `Week ${weekNum}`,
            posts: []
        };

        for (const post of posts) {
            const pid = String(post.post_id);
            const status = tracker.posts?.[pid] || {};

            weekSection.posts.push({
                id: pid,
                date: post.date,
                title: post.title,
                tier: post.tier,
                platforms: (post.platforms || []).map(p => p.name || p.key),
                content_type: post.content_type,
                copy_a: post.copy?.option_a || '',
                visual_direction: post.visual?.direction_a || '',
                creative_mode: status.creative_mode || '',
                status: status.status || 'QUEUED'
            });
        }

        doc.sections.push(weekSection);
    }

    // Publishing schedule
    doc.sections.push({
        type: 'schedule',
        title: 'Publishing Schedule',
        entries: (calendar.posts || []).map(p => ({
            date: p.date,
            day: p.day_of_week,
            post_id: p.post_id,
            title: p.title,
            platforms: (p.platforms || []).map(pl => pl.name || pl.key).join(', ')
        }))
    });

    return doc;
}

function main() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.log(JSON.stringify({ error: 'Usage: assemble_docx.js <brand> <month>' }));
        process.exit(1);
    }

    const [brand, month] = args;
    const doc = buildDocxStructure(brand, month);

    if (doc.error) {
        console.log(JSON.stringify(doc));
        process.exit(1);
    }

    // Save the DOCX-ready JSON structure
    const outputDir = path.join(WORKSPACE, 'output', brand, month, 'FINAL', '00-Calendar-Document');
    fs.mkdirSync(outputDir, { recursive: true });

    const jsonPath = path.join(outputDir, `${brand}-${month}-calendar.json`);
    fs.writeFileSync(jsonPath, JSON.stringify(doc, null, 2), 'utf-8');

    console.log(JSON.stringify({
        status: 'success',
        brand: brand,
        month: month,
        output_contract: 'DOCX-ready JSON structure',
        json_output: jsonPath,
        docx_output: null,
        docx_note: 'DOCX emission is not implemented — the `docx` npm package is not a shipped dependency. Convert the JSON structure downstream.',
        sections: doc.sections.length,
        posts: doc.sections.filter(s => s.type === 'week').reduce((sum, w) => sum + w.posts.length, 0)
    }, null, 2));
}

main();
