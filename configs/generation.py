infile = open('template.json', 'r')
latex = infile.read()
infile.close()
latex = latex.replace('{','|')
latex = latex.replace('[[','{')
latex = latex.replace('}','&')
latex = latex.replace(']]','}')

data = open('configs.csv', 'r')
for i, line in enumerate(data.readlines()[1:]):
    line = [num.strip() for num in line.split(';')]
    dic = {str(i+1):'' for i in range(5)}
    dic['q'] = line[0]
    dic['w'] = line[1]
    dic['e'] = line[2]
    dic['r'] = line[3]
    dic['t'] = line[4]
    tmp_output = latex.format(**dic)
    tmp_output = tmp_output.replace('|', '{')
    tmp_output = tmp_output.replace('&', '}')

    outfile = open('conf_' + line[0] + '_' + str(i%15) + '.json', 'w')
    outfile.write(tmp_output)
    outfile.close()
