-- text_color_and_align.lua

-- ==========================================
-- 1. SPAN PROCESSOR (For Text & Background Colors)
-- ==========================================
function Span(el)
  local style = el.attributes['style']
  if not style then return nil end

  local color_val = nil
  local bg_val = nil

  -- Loop through all CSS properties to prevent 'background-color' from matching 'color'
  for prop, hex in style:gmatch('([%a%-]+):%s*(#[%da-fA-F]+)') do
    if prop == 'color' then
      color_val = hex:sub(2):upper()
    elseif prop == 'background-color' then
      bg_val = hex:sub(2):upper()
    end
  end
  
  if not color_val and not bg_val then return nil end

  -- For Raw LaTeX or PDF via LaTeX
  if FORMAT:match 'latex' or FORMAT:match 'beamer' then
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\colorbox[HTML]{' .. bg_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\textcolor[HTML]{' .. color_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    return el

  -- For Typst (Raw .typ or PDF via Typst)
  elseif FORMAT:match 'typst' then
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#text(fill: rgb("#' .. color_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#highlight(fill: rgb("#' .. bg_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    return el

  -- For Word (DOCX)
  elseif FORMAT:match 'docx' then
    local styleName = ""
    
    if color_val then styleName = styleName .. "Color" .. color_val end
    if bg_val then styleName = styleName .. "Bg" .. bg_val end
    
    el.attributes['custom-style'] = styleName
    -- We can safely remove the style attribute for DOCX so it doesn't cause bloat
    el.attributes['style'] = nil 
    return el
  end
end

-- ==========================================
-- 2. DIV PROCESSOR (For Block Alignment)
-- ==========================================
function Div(el)
  local c_style = el.attributes['custom-style']
  if not c_style then return nil end

  -- Check if the custom-style is one of our align-* styles
  local align = c_style:match('^align%-(.+)$')
  if not align then return nil end

  -- For Raw LaTeX or PDF via LaTeX
  if FORMAT:match 'latex' or FORMAT:match 'beamer' then
    local env = nil
    if align == 'center' then 
      env = 'center'
    elseif align == 'right' then 
      env = 'flushright'
    elseif align == 'justify' then
      -- Note: LaTeX text is justified by default. 
      -- We leave it as a standard block unless you are using the 'ragged2e' package, 
      -- in which case you could set env = 'justify'.
    end
    
    if env then
      -- Since Divs contain block elements, we must insert RawBlocks (not RawInlines)
      table.insert(el.content, 1, pandoc.RawBlock('latex', '\\begin{' .. env .. '}'))
      table.insert(el.content, pandoc.RawBlock('latex', '\\end{' .. env .. '}'))
    end
    return el

  -- For Typst (Raw .typ or PDF via Typst)
  elseif FORMAT:match 'typst' then
    if align == 'center' or align == 'right' then
      table.insert(el.content, 1, pandoc.RawBlock('typst', '#align(' .. align .. ')[ \n'))
      table.insert(el.content, pandoc.RawBlock('typst', '\n]'))
    elseif align == 'justify' then
      -- Typst handles justification via the par() function
      table.insert(el.content, 1, pandoc.RawBlock('typst', '#par(justify: true)[ \n'))
      table.insert(el.content, pandoc.RawBlock('typst', '\n]'))
    end
    return el

  -- For Word (DOCX)
  elseif FORMAT:match 'docx' then
    -- Pandoc NATIVELY supports the `custom-style` attribute on Div blocks for DOCX!
    -- Because your markdown is `::: {custom-style="align-center"}`, Pandoc will 
    -- automatically look for a Paragraph Style named "align-center" in your reference doc.
    -- Therefore, we don't need to modify the AST for DOCX at all; we just let it pass through.
    return el
  end
end