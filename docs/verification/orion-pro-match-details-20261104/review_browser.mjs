async (page) => {
  const root = '/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-pro-match-details-20261104';
  const output = `${root}/output/playwright/native-review`;
  const target = `file://${root}/NATIVE_MODEL_REVIEW.html`;
  const requests = [], pageErrors = [], consoleErrors = [], cases = [];
  page.on('request', request => requests.push({url: request.url(), method: request.method()}));
  page.on('pageerror', error => pageErrors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const record = (name, actual) => cases.push({case: name, status: 'pass', actual});
  try {
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(target, {waitUntil: 'load'});
    const data = await page.locator('#review-data').textContent().then(JSON.parse);
    assert(await page.getByRole('heading', {name: 'Détails natifs du match', exact: true}).count() === 1, 'Missing review heading');
    assert(await page.locator('#proposal-state').textContent() === 'Proposition — non appliquée', 'Approval state unclear');
    assert(data.delta.before.all.tables === 103 && data.delta.after.all.tables === 107, 'Wrong table counts');
    assert(data.delta.after.all.columns - data.delta.before.all.columns === 114, 'Wrong column delta');
    assert(data.delta.after.all.foreignKeys - data.delta.before.all.foreignKeys === 16, 'Wrong FK delta');
    assert(data.delta.after.all.jsonbColumns === data.delta.before.all.jsonbColumns, 'JSONB changed');
    record('proposal_and_computed_counts', {before: data.delta.before, after: data.delta.after, baseSha256: data.baseSha256});
    assert(await page.locator('[data-new-child]').count() === 4, 'Four children missing from diagram');
    for (const q of ['ingest.match_coverage', 'ingest.source_records', 'football.team_match_metric_values']) {
      assert(await page.locator('#parent-diagram').getByText(q, {exact: true}).count() === 1, `Missing diagram parent ${q}`);
    }
    record('four_children_and_existing_parents', {newChildren: await page.locator('[data-new-child]').count()});
    await page.screenshot({path: `${output}/01-amendment-desktop.png`, fullPage: true});
    await page.getByRole('tab', {name: '114 colonnes', exact: true}).click();
    assert(await page.locator('#dictionary-rows tr').count() === 114, 'Dictionary is incomplete');
    const firstCells = await page.locator('#dictionary-rows tr').first().locator('td').count();
    assert(firstCells === 7, 'Dictionary must show table, column, type, key, nullable, state, role');
    record('dictionary_all_added_columns', {rows: 114, fieldsPerRow: firstCells});
    await page.getByRole('searchbox', {name: 'Rechercher dans les 114 colonnes'}).fill('source_finished');
    const filtered = await page.locator('#dictionary-rows tr').allTextContents();
    assert(filtered.length === 2 && filtered.some(x => x.includes('boolean')), 'Dictionary search misses native finished boolean/state');
    record('dictionary_search', {query: 'source_finished', rows: filtered});
    await page.getByRole('searchbox', {name: 'Rechercher dans les 114 colonnes'}).fill('');
    await page.getByRole('tab', {name: '107 tables', exact: true}).click();
    assert(await page.locator('#table-list > button').count() === 107, 'Catalogue omits tables');
    await page.locator('[data-table="football.match_team_stat_items"]').click();
    assert(await page.locator('#selected-columns tr').count() === 15, 'Stat item catalogue columns incomplete');
    assert(await page.locator('#table-detail').getByText('match_team_stat_items_home_metric_fk', {exact: true}).count() === 1, 'Outgoing FK definition missing');
    record('catalogue_all_tables_and_relationships', {tables: 107, selectedTable: 'football.match_team_stat_items', selectedColumns: 15});
    await page.getByRole('searchbox', {name: 'Rechercher parmi toutes les tables, colonnes et relations'}).fill('request_fingerprint');
    assert(await page.locator('[data-table="ingest.source_documents"]').count() === 1, 'Search is not global across retained columns');
    await page.locator('[data-table="ingest.source_documents"]').click();
    assert((await page.locator('#selected-columns').textContent()).includes('request_fingerprint'), 'Retained table content omitted');
    record('global_retained_column_search', {query: 'request_fingerprint', table: 'ingest.source_documents'});
    await page.getByRole('searchbox', {name: 'Rechercher parmi toutes les tables, colonnes et relations'}).fill('');
    const filteredCounts = {};
    for (const [value, expected] of [['new',4], ['modified',7], ['retained',96], ['all',107]]) {
      await page.getByLabel('Modification', {exact: true}).selectOption(value);
      filteredCounts[value] = await page.locator('#table-list > button').count();
      assert(filteredCounts[value] === expected, `Wrong change filter ${value}`);
    }
    record('new_modified_retained_filters', filteredCounts);
    await page.screenshot({path: `${output}/02-catalogue-desktop.png`, fullPage: true});
    await page.getByRole('tab', {name: 'Contraintes', exact: true}).click();
    assert(await page.locator('#added-fks > details').count() === 16, 'Added FK list incomplete');
    assert(await page.locator('#cross-row-rules > details').count() === 7, 'Cross-row rules omitted');
    assert(await page.locator('#replacement-rows tr').count() === 4, 'Four replacements missing');
    assert(await page.locator('#replaced-checks > details').count() === 2, 'Numeric finite CHECK replacements missing');
    assert(await page.locator('#added-checks > details').count() === 128, 'Added CHECK list incomplete');
    const unimplemented = await page.locator('#rule-state').textContent();
    assert(unimplemented.includes('non implémentées'), 'Rule implementation state misleading');
    record('constraints_replacements_and_pending_rules', {addedForeignKeys:16, addedChecks:128, replacements:4, replacedChecks:2, unimplementedRules:7, state:unimplemented});
    await page.getByRole('tab', {name: 'Limites', exact: true}).click();
    assert(await page.locator('#limits-list > li').count() === 8, 'Uncovered/unaccepted shapes missing');
    record('explicit_uncovered_shapes', {shapes: 8});
    await page.getByRole('tab', {name: 'Amendement', exact: true}).click();
    await page.setViewportSize({width: 390, height: 844});
    const mobile = await page.evaluate(() => ({viewport: innerWidth, width: document.documentElement.scrollWidth,
      tabs: [...document.querySelectorAll('[role=tab]')].map(e => ({text:e.textContent, height:e.getBoundingClientRect().height}))}));
    assert(mobile.width <= mobile.viewport, 'Page-wide mobile overflow');
    assert(mobile.tabs.every(x => x.height >= 40), 'Mobile tab targets too small');
    await page.screenshot({path: `${output}/03-amendment-mobile.png`, fullPage: true});
    await page.getByRole('tab', {name: '107 tables', exact: true}).click();
    await page.getByRole('searchbox', {name: 'Rechercher parmi toutes les tables, colonnes et relations'}).fill('source_finished');
    assert(await page.locator('[data-table="football.match_h2h_entries"]').count() === 1, 'Mobile catalogue search unusable');
    await page.screenshot({path: `${output}/04-catalogue-mobile.png`, fullPage: true});
    record('mobile_controls_and_search', mobile);
    const external = requests.filter(x => !x.url.startsWith('file:') && !x.url.startsWith('data:'));
    assert(external.length === 0, `Unexpected external requests: ${JSON.stringify(external)}`);
    assert(pageErrors.length === 0 && consoleErrors.length === 0, 'Browser errors');
    record('no_external_requests_or_browser_errors', {requests, external, pageErrors, consoleErrors});
    return {kind:'LOCAL_STANDALONE_REVIEW_BROWSER_E2E', status:'pass', passed:cases.length, cases,
      setup:{target, browser: page.context().browser().version(), viewportDesktop:[1440,1000], viewportMobile:[390,844], servicesStarted:0},
      requests,pageErrors,consoleErrors, databaseUsed:false, sqlExecuted:false, cloudUsed:false,
      sourceBodyRead:false, modelApproval:false, constraintExecutionValidated:false};
  } catch (error) {
    await page.screenshot({path:`${output}/99-failure.png`, fullPage:true}).catch(() => {});
    return {kind:'LOCAL_STANDALONE_REVIEW_BROWSER_E2E',status:'fail',passed:cases.length,cases,error:String(error),requests,pageErrors,consoleErrors};
  }
}
